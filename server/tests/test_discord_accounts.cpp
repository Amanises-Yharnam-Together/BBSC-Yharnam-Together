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
constexpr qint64 Now = 1'800'000'000;

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
  const QString secret = Secret(key, id, Now);
  CHECK(secret.size() == 32);
  CHECK(secret == Secret(key, id, Now));
  CHECK(secret != Secret(key, OnlineId(key, "1"), Now));
  CHECK(secret != Secret(key, id, Now + 1)); // each sign-in its own
  CHECK(!secret.contains(id.mid(1, 8)));     // not the id again
  return 0;
}

int AHelloIsTold() {
  const QByteArray key = KeyFrom(LinkSecret);
  const QByteArray id = OnlineId(key, "42").toLatin1();
  const QByteArray secret =
      Secret(key, QString::fromLatin1(id), Now).toLatin1();
  CHECK(Check(key, id, secret, Now, 0) == Verdict::Good);
  // Any shard: it holds the link key, and no store is asked.
  CHECK(Check(KeyFrom(LinkSecret), id, secret, Now + 60, 0) == Verdict::Good);
  CHECK(Check(key, id, QByteArray(32, 'a'), Now, 0) == Verdict::Forged);
  CHECK(Check(key, id, secret.left(31), Now, 0) == Verdict::Forged);
  CHECK(Check(key, "p0123456789abcd", secret, Now, 0) == Verdict::Forged);
  CHECK(Check(key, OnlineId(key, "43").toLatin1(), secret, Now, 0) ==
        Verdict::Forged);
  CHECK(Check(KeyFrom(OtherSecret), id, secret, Now, 0) == Verdict::Forged);
  CHECK(Check({}, id, secret, Now, 0) == Verdict::Forged); // no key: never
  // A later date typed into it breaks the signature.
  QByteArray tampered = secret;
  tampered[7] = tampered[7] == '0' ? '1' : '0';
  CHECK(Check(key, id, tampered, Now, 0) == Verdict::Forged);
  tampered = secret;
  tampered[31] = tampered[31] == '0' ? '1' : '0';
  CHECK(Check(key, id, tampered, Now, 0) == Verdict::Forged);
  return 0;
}

int ASecretHolds30Days() {
  const QByteArray key = KeyFrom(LinkSecret);
  const QByteArray id = OnlineId(key, "42").toLatin1();
  const QByteArray secret =
      Secret(key, QString::fromLatin1(id), Now).toLatin1();
  const qint64 days = 24 * 3600;
  CHECK(Check(key, id, secret, Now + 30 * days, 0) == Verdict::Good);
  CHECK(Check(key, id, secret, Now + 30 * days + 1, 0) == Verdict::Expired);
  // A new sign-in: another secret, and it works.
  const QByteArray again =
      Secret(key, QString::fromLatin1(id), Now + 30 * days + 1).toLatin1();
  CHECK(again != secret);
  CHECK(Check(key, id, again, Now + 30 * days + 1, 0) == Verdict::Good);
  return 0;
}

int ASignOutKillsTheOlderOnes() {
  const QByteArray key = KeyFrom(LinkSecret);
  const QByteArray id = OnlineId(key, "42").toLatin1();
  const QByteArray older = Secret(key, QString::fromLatin1(id), Now).toLatin1();
  const QByteArray newer =
      Secret(key, QString::fromLatin1(id), Now + 10).toLatin1();
  CHECK(Check(key, id, older, Now + 20, Now + 5) == Verdict::SignedOut);
  CHECK(Check(key, id, newer, Now + 20, Now + 5) == Verdict::Good);
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
  failed |= ASecretHolds30Days();
  failed |= ASignOutKillsTheOlderOnes();
  failed |= TheRedirectIsOurs();
  failed |= TheAddressIsTheConnections();
  if (failed == 0) {
    std::cout << "discord accounts: all checks passed\n";
  }
  return failed;
}
