// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Global servers: a player's account comes from Discord, never from a login or a password
// (docs/HOSTED_SERVER.md, "Sign in with Discord"). One Discord user is one account on every shard
// of a region and every PC: its online id and its secret are made from the Discord user id with a
// key only the server holds, itself made from the link key every shard of a region shares. So any
// shard can answer a sign-in and any shard can tell a sign-in's secret at a hello, with no store
// shared between them; a fresh random secret would be stale on the other shards.
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
constexpr qsizetype SecretHexChars = 32;

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

inline QString Secret(const QByteArray& key, const QString& online_id) {
    return QString::fromLatin1(
        Mac(key, "secret|" + online_id.toUtf8()).toHex().left(SecretHexChars));
}

// Whether `secret` is what a Discord sign-in gave `online_id`.
inline bool Holds(const QByteArray& key, const QByteArray& online_id, const QByteArray& secret) {
    if (key.isEmpty() || online_id.size() != IdHexChars + 1 || !online_id.startsWith('d')) {
        return false;
    }
    const QByteArray want = Secret(key, QString::fromLatin1(online_id)).toLatin1();
    if (want.size() != secret.size()) {
        return false;
    }
    quint8 differs = 0;
    for (qsizetype i = 0; i < want.size(); ++i) {
        differs |= static_cast<quint8>(want[i] ^ secret[i]);
    }
    return differs == 0;
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
