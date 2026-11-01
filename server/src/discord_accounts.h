// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Global servers: a player's account comes from Discord, never from a login or a password
// (docs/HOSTED_SERVER.md, "Sign in with Discord"). One Discord user is one account on every shard
// of a region and every PC: its online id is made from the Discord user id with a key only the
// server holds, itself made from the link key every shard of a region shares. Its secret is signed
// with that key and says when it was issued, so any shard can tell it at a hello with no store
// shared between them. A secret holds SecretDays; each sign-in gives a new one, and a sign out
// kills the older ones (Database::DiscordNotBefore, each shard's own).
#pragma once

#include <span>

#include <QByteArray>
#include <QCryptographicHash>
#include <QMessageAuthenticationCode>
#include <QRegularExpression>
#include <QString>
#include <QStringList>
#include <QtGlobal>

namespace DiscordAccounts {

// Tries for a free virtual address (two ids can share one, which the accounts refuse).
constexpr int SaltTries = 16;
constexpr qsizetype IdHexChars = 14; // "d" and these: a valid id, as the launcher's "p" ids
constexpr qsizetype IssuedHexChars = 8;
constexpr qsizetype SecretHexChars = 32; // the issue time, then the signature
constexpr qint64 SecretDays = 30;

inline QByteArray Mac(const QByteArray& key, const QByteArray& text) {
    return QMessageAuthenticationCode::hash(text, key, QCryptographicHash::Sha256);
}

// The accounts' key from the link's secret key.
inline QByteArray KeyFrom(std::span<const quint8> link_secret) {
    return Mac(QByteArray(reinterpret_cast<const char*>(link_secret.data()),
                          static_cast<qsizetype>(link_secret.size())),
               "bloodborne discord accounts v1");
}

// `salt`: the try, when an earlier id's virtual address is another account's.
inline QString OnlineId(const QByteArray& key, const QString& discord_user, int salt = 0) {
    const QByteArray text = "id|" + discord_user.toUtf8() + "|" + QByteArray::number(salt);
    return "d" + QString::fromLatin1(Mac(key, text).toHex().left(IdHexChars));
}

// The secret a sign-in at `issued_s` (unix seconds) gives `online_id`.
inline QString Secret(const QByteArray& key, const QString& online_id, qint64 issued_s) {
    const QByteArray issued =
        QByteArray::number(issued_s, 16).rightJustified(IssuedHexChars, '0').right(IssuedHexChars);
    const QByteArray signature = Mac(key, "secret|" + online_id.toUtf8() + "|" + issued).toHex();
    return QString::fromLatin1(issued + signature.left(SecretHexChars - IssuedHexChars));
}

// Whether `online_id` has the shape of a sign-in's id (no other account's secret is told here).
inline bool IsDiscordId(const QByteArray& online_id) {
    return online_id.size() == IdHexChars + 1 && online_id.startsWith('d');
}

enum class Verdict { Good, Forged, Expired, SignedOut };

// `secret` at a hello: signed for this id, not older than SecretDays, and not from before the
// account's last sign out (`not_before_s`).
inline Verdict Check(const QByteArray& key, const QByteArray& online_id, const QByteArray& secret,
                     qint64 now_s, qint64 not_before_s) {
    if (key.isEmpty() || !IsDiscordId(online_id) || secret.size() != SecretHexChars) {
        return Verdict::Forged;
    }
    bool hex = false;
    const qint64 issued = secret.left(IssuedHexChars).toLongLong(&hex, 16);
    if (!hex) {
        return Verdict::Forged;
    }
    const QByteArray want = Secret(key, QString::fromLatin1(online_id), issued).toLatin1();
    quint8 differs = 0;
    for (qsizetype i = 0; i < want.size(); ++i) {
        differs |= static_cast<quint8>(want[i] ^ secret[i]);
    }
    if (differs != 0) {
        return Verdict::Forged;
    }
    if (issued > now_s + 300 || now_s - issued > SecretDays * 24 * 3600) {
        return Verdict::Expired;
    }
    return issued < not_before_s ? Verdict::SignedOut : Verdict::Good;
}

// The launcher's loopback address, on one of the fixed ports registered with Discord.
inline bool ValidRedirect(const QString& uri, const QStringList& ports) {
    static const QRegularExpression shape{
        QStringLiteral(R"(^http://127\.0\.0\.1:(\d{1,5})/discord$)")};
    const QRegularExpressionMatch match = shape.match(uri);
    return match.hasMatch() && ports.contains(match.captured(1));
}

// The address a sign-in counts against: the connection's, or behind our own TLS proxy
// (DiscordProxied) the one the proxy added last: anything before it the client typed itself.
inline QString ClientAddress(const QString& connection, const QByteArray& forwarded_for,
                             bool proxied) {
    if (!proxied || forwarded_for.trimmed().isEmpty()) {
        return connection;
    }
    return QString::fromLatin1(forwarded_for.split(',').constLast().trimmed());
}

} // namespace DiscordAccounts
