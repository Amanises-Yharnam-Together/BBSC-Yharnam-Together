// SPDX-FileCopyrightText: Copyright 2026 shadNet Project
// SPDX-License-Identifier: GPL-2.0-or-later
// One Discord user, one account, on every shard and PC; what a hello can tell
// (discord_accounts.h).
#include <array>
#include <iostream>

#include "discord_accounts.h"

#define CHECK(condition)                                                       \
  if (!(condition)) {                                                          \
    std::cerr << "FAILED " << __LINE__ << ": " #condition "\n";                \
    return 1;                                                                  \
  }

using namespace DiscordAccounts;

namespace {

const std::array<quint8, 32> LinkSecret{1, 2, 3};
const std::array<quint8, 32> OtherSecret{9, 9, 9};

int OneUserIsOneAccount() {
  const QByteArray key = KeyFrom(LinkSecret);
  CHECK(key ==
        KeyFrom(LinkSecret)); // every shard of a region holds this link key
  CHECK(key != KeyFrom(OtherSecret));
  const QString id = OnlineId(key, "80351110224678912");
  CHECK(id == OnlineId(key, "80351110224678912"));
  CHECK(id != OnlineId(key, "80351110224678913"));
  CHECK(id != OnlineId(key, "80351110224678912",
                       1)); // the next try for a free address
  CHECK(id != OnlineId(KeyFrom(OtherSecret), "80351110224678912"));
  // As the launcher's own ids: a valid name, a valid secret.
  CHECK(id.size() == 15 && id.startsWith('d'));
  const QString secret = Secret(key, id);
  CHECK(secret.size() == 32);
  CHECK(secret == Secret(key, id));
  CHECK(secret != Secret(key, OnlineId(key, "1")));
  CHECK(!secret.contains(id.mid(1, 8))); // not the id again
  return 0;
}

int AHelloIsTold() {
  const QByteArray key = KeyFrom(LinkSecret);
  const QString id = OnlineId(key, "42");
  const QByteArray secret = Secret(key, id).toLatin1();
  CHECK(Holds(key, id.toLatin1(), secret));
  CHECK(!Holds(key, id.toLatin1(), QByteArray(32, 'a')));
  CHECK(!Holds(key, id.toLatin1(), secret.left(31)));
  CHECK(!Holds(key, "p0123456789abcd", secret)); // a home server's kind of id
  CHECK(!Holds(KeyFrom(OtherSecret), id.toLatin1(), secret));
  CHECK(!Holds({}, id.toLatin1(), secret)); // no key: never
  return 0;
}

int TheRedirectIsOurs() {
  const QStringList ports{"47231", "47232"};
  CHECK(ValidRedirect("http://127.0.0.1:47231/discord", ports));
  CHECK(ValidRedirect("http://127.0.0.1:47232/discord", ports));
  CHECK(!ValidRedirect("http://127.0.0.1:47233/discord", ports));
  CHECK(!ValidRedirect("http://127.0.0.1:47231/other", ports));
  CHECK(!ValidRedirect("http://evil.example.com:47231/discord", ports));
  CHECK(!ValidRedirect("https://127.0.0.1:47231/discord", ports));
  CHECK(!ValidRedirect("http://127.0.0.1:47231/discord?x=1", ports));
  return 0;
}

int TheAddressIsTheConnections() {
  CHECK(ClientAddress("203.0.113.7", "", false) == "203.0.113.7");
  // Not behind our proxy: a header anyone can send is ignored.
  CHECK(ClientAddress("203.0.113.7", "198.51.100.1", false) == "203.0.113.7");
  CHECK(ClientAddress("127.0.0.1", "198.51.100.1", true) == "198.51.100.1");
  // What the client typed comes first; the proxy adds the real one last.
  CHECK(ClientAddress("127.0.0.1", "1.1.1.1, 198.51.100.1", true) ==
        "198.51.100.1");
  CHECK(ClientAddress("127.0.0.1", "", true) == "127.0.0.1");
  return 0;
}

} // namespace

int main() {
  int failed = 0;
  failed |= OneUserIsOneAccount();
  failed |= AHelloIsTold();
  failed |= TheRedirectIsOurs();
  failed |= TheAddressIsTheConnections();
  if (failed == 0) {
    std::cout << "discord accounts: all checks passed\n";
  }
  return failed;
}
