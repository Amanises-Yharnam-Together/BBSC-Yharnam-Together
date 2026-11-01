// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <QByteArray>

#include "config.h"

class Database;
class QHttpServer;
class QObject;

namespace WebApiRoutes {

// GET /bb/discord/config (what the launcher needs to open Discord's page) and POST
// /bb/discord/sign-in {code, code_verifier, redirect_uri}: 200 {id, secret, name}, and POST
// /bb/discord/sign-out {id, secret}. Only when
// DiscordConfig::Enabled() and `key` (DiscordAccounts::KeyFrom) is known; `owner` lives as long as
// the server.
void RegisterDiscordRoutes(QHttpServer& http, Database& db, const DiscordConfig& config,
                           const QByteArray& key, QObject* owner);

} // namespace WebApiRoutes
