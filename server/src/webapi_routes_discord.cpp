// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// Sign in with Discord (docs/HOSTED_SERVER.md): the launcher's OAuth2 code becomes the one account
// of that Discord user. The launcher reaches this over HTTPS only; the Discord token is used for
// one request and forgotten, and neither it, the code nor the client secret is ever logged.
#include <memory>

#include <QDateTime>
#include <QDebug>
#include <QHostAddress>
#include <QHttpServer>
#include <QHttpServerRequest>
#include <QHttpServerResponder>
#include <QHttpServerResponse>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrlQuery>

#include "bloodborne_reports.h"
#include "database.h"
#include "discord_accounts.h"
#include "virtual_address.h"
#include "webapi_routes_discord.h"

namespace {

constexpr int DiscordTimeoutMs = 10'000;

QHttpServerResponse Answer(const QJsonObject& body, QHttpServerResponder::StatusCode status =
                                                        QHttpServerResponder::StatusCode::Ok) {
    return QHttpServerResponse{"application/json",
                               QJsonDocument(body).toJson(QJsonDocument::Compact), status};
}

QHttpServerResponse Refused(QHttpServerResponder::StatusCode status, const char* why) {
    return Answer(QJsonObject{{"error", QString::fromLatin1(why)}}, status);
}

// The id of this Discord user: its account if it has one, else the first with a free address.
std::optional<QString> IdFor(Database& db, const QByteArray& key, const QString& user) {
    for (int salt = 0; salt < DiscordAccounts::SaltTries; ++salt) {
        const QString id = DiscordAccounts::OnlineId(key, user, salt);
        if (db.GetUserId(id) || !db.AddressTaken(VirtualAddressOf(id.toUtf8()))) {
            return id;
        }
    }
    return std::nullopt;
}

} // namespace

namespace WebApiRoutes {

void RegisterDiscordRoutes(QHttpServer& http, Database& db, const DiscordConfig& config,
                           const QByteArray& key, QObject* owner) {
    http.route("/bb/discord/config", QHttpServerRequest::Method::Get, [config] {
        QJsonArray ports;
        for (const QString& port : config.redirectPorts) {
            ports.append(port.toInt());
        }
        return Answer(QJsonObject{{"client_id", config.clientId}, {"ports", ports}});
    });
    auto limiter = std::make_shared<ReportLimiter>(config.signInsPerMinute, 60'000);
    auto net = std::make_shared<QNetworkAccessManager>(owner);
    http.route("/bb/discord/sign-in", QHttpServerRequest::Method::Post,
               [&db, config, key, limiter, net, owner](const QHttpServerRequest& request,
                                                       QHttpServerResponder& responder) {
                   using Status = QHttpServerResponder::StatusCode;
                   const QString address = DiscordAccounts::ClientAddress(
                       request.remoteAddress().toString(), request.value("X-Forwarded-For"),
                       config.proxied);
                   if (!limiter->Allow(qHash(address), QDateTime::currentMSecsSinceEpoch())) {
                       responder.sendResponse(Refused(Status::TooManyRequests, "slow down"));
                       return;
                   }
                   const QJsonObject body = QJsonDocument::fromJson(request.body()).object();
                   const QString code = body.value("code").toString();
                   const QString verifier = body.value("code_verifier").toString();
                   const QString redirect = body.value("redirect_uri").toString();
                   if (code.isEmpty() || verifier.isEmpty() ||
                       !DiscordAccounts::ValidRedirect(redirect, config.redirectPorts)) {
                       responder.sendResponse(Refused(Status::BadRequest, "bad request"));
                       return;
                   }
                   QUrlQuery form;
                   form.addQueryItem("client_id", config.clientId);
                   form.addQueryItem("client_secret", config.clientSecret);
                   form.addQueryItem("grant_type", "authorization_code");
                   form.addQueryItem("code", code);
                   form.addQueryItem("redirect_uri", redirect);
                   form.addQueryItem("code_verifier", verifier);
                   QNetworkRequest token_request{QUrl{config.apiBase + "/oauth2/token"}};
                   token_request.setHeader(QNetworkRequest::ContentTypeHeader,
                                           "application/x-www-form-urlencoded");
                   token_request.setTransferTimeout(DiscordTimeoutMs);
                   QNetworkReply* exchange =
                       net->post(token_request, form.toString(QUrl::FullyEncoded).toUtf8());
                   auto waiting = std::make_shared<QHttpServerResponder>(std::move(responder));
                   QObject::connect(exchange, &QNetworkReply::finished, owner, [=, &db] {
                       exchange->deleteLater();
                       const int said =
                           exchange->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
                       const QJsonObject tokens =
                           QJsonDocument::fromJson(exchange->readAll()).object();
                       const QString token = tokens.value("access_token").toString();
                       if (said == 0) {
                           qWarning().noquote() << "Discord sign-in: Discord does not answer";
                           waiting->sendResponse(Refused(Status::BadGateway, "discord is down"));
                           return;
                       }
                       if (token.isEmpty()) {
                           qInfo().noquote() << "Discord sign-in: a code refused (" << said << ")";
                           waiting->sendResponse(Refused(Status::Unauthorized, "code refused"));
                           return;
                       }
                       QNetworkRequest me_request{QUrl{config.apiBase + "/users/@me"}};
                       me_request.setRawHeader("Authorization", "Bearer " + token.toUtf8());
                       me_request.setTransferTimeout(DiscordTimeoutMs);
                       QNetworkReply* me = net->get(me_request);
                       QObject::connect(me, &QNetworkReply::finished, owner, [=, &db] {
                           me->deleteLater();
                           const QJsonObject user = QJsonDocument::fromJson(me->readAll()).object();
                           const QString discord_id = user.value("id").toString();
                           if (discord_id.isEmpty()) {
                               waiting->sendResponse(Refused(Status::BadGateway, "no such user"));
                               return;
                           }
                           const auto id = IdFor(db, key, discord_id);
                           if (!id) {
                               qWarning().noquote() << "Discord sign-in: no free address";
                               waiting->sendResponse(
                                   Refused(Status::ServiceUnavailable, "try again later"));
                               return;
                           }
                           QString name = user.value("global_name").toString();
                           if (name.isEmpty()) {
                               name = user.value("username").toString();
                           }
                           qInfo().noquote() << "Discord sign-in:" << *id;
                           waiting->sendResponse(Answer(QJsonObject{
                               {"id", *id},
                               {"secret", DiscordAccounts::Secret(key, *id)},
                               {"name", name},
                           }));
                       });
                   });
               });
}

} // namespace WebApiRoutes
