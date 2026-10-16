# Katalogrichtlinie

Der eingebaute Katalog enthält **527 Dienste**. Er ist eine lokale Hilfe für den
Domain-Abgleich, keine Liste nachgewiesener Accounts und kein Dienst-Scanner. Die
App vergleicht eine Absenderdomain aus einer lokalen E-Mail mit einer kuratierten
Domainwurzel. Sie sendet diese Adresse weder an Anbieter noch fragt sie ab, ob ein
Account existiert.

## Bedeutung eines Eintrags

Ein Eintrag enthält stabile ID, Anzeigename, offizielle HTTPS-Website, Kategorie
und eine oder mehrere Absenderdomainwurzeln. Ein Treffer erzeugt nur dann einen
Hinweis, wenn auch der lokale Mailinhalt zu einer Erkennungsregel passt. Das kann
höchstens zu „Wahrscheinlich“ führen. Erst die Prüfung durch den Nutzer macht
einen Account „Bestätigt“.

Ein Eintrag behauptet nicht, dass jeder Dienst von der genannten Domain sendet,
dass jede Mail dieser Domain einen Account beweist oder dass der Anbieter in jedem
Land aktiv ist. Newsletter, Gastbestellungen und Passwort-Reset-Anforderungen
reichen bewusst nicht allein aus.

## Auswahl- und Prüfregeln

- Einen eigenständigen Dienst mit offizieller HTTPS-Website und einer stabilen,
  vom Dienst kontrollierten Absenderdomainwurzel ergänzen.
- Die kleinste passende Wurzel verwenden. Keine allgemeinen Versand-, Analyse-,
  Hosting- oder Zahlungsanbieter-Domains einem anderen Dienst zuordnen.
- IDs klein und stabil halten. Keine vorhandene ID oder Domainwurzel wiederverwenden.
- Domains nicht nur aus Markenname oder Absenderanzeige ableiten.
- Einen Passwort-Direktlink nur mit offizieller HTTPS-Quelle und Prüfdaten setzen;
  sonst weglassen.
- Den Katalog mit der Testsuite prüfen. Das Registry-Modul lehnt doppelte Wurzeln,
  unsichere Links und mehrdeutige Zuordnungen ab.

Der Katalog ist kuratiert, aber kein Live-Verfügbarkeitscheck. Dienste,
Absenderdomains und Passwort-Einstellungen können sich ändern. Die getrennte
Prüfbasis für die eingebauten Passwortlinks steht unter
[offizielle Quellen](SOURCES.md).

## Gemeinsam genutzte Versanddienste

Massenmail-Plattformen wie `sendgrid.net`, `amazonses.com`, `mailgun.org` oder
`mcsv.net` versenden für viele Firmen. Ihre Domains bezeichnen nie einen Dienst.
Das Registry-Modul lehnt sie in jedem Katalog ab (eingebaut, `--providers`-Datei
und eigene Ergänzungen im Profil), und das Dashboard kennzeichnet Hinweise von
ihnen als gemeinsam genutzten Versanddienst. Die Liste steht in
`argus_security/registry.py` (`SHARED_SENDERS`); Erweiterungen bitte in einem
eigenen Pull Request mit offizieller Quelle je Domain.

## Dienste vorschlagen

Am einfachsten über das Issue-Formular **Dienst vorschlagen**. Es fragt nach
offizieller HTTPS-Website, Kategorie, jeder Domainwurzel mit Begründung,
öffentlichen Quellen mit Prüfdatum und vier Prüfkriterien. Alternativ einen Pull
Request mit ausschließlich künstlichen Beispielen eröffnen. Offizielle Website, vorgeschlagene Domainwurzeln, Kategorie
und die Begründung für jede Wurzel nennen. Keine echten E-Mails, Header mit
persönlichen Adressen oder Account-Listen anhängen. Unabhängige Katalogänderungen
nicht im selben Pull Request mischen.

Für private Ergänzungen unter „Unklares“ im Dashboard **Zu meinem Katalog
hinzufügen** wählen; der Eintrag wird wie dieser Katalog geprüft und bleibt in
deinem Profil (`my-providers.json`). Alternativ eine separate JSON-Datei anlegen
und die App mit `--providers pfad/zu/providers-extra.json` starten. Der eingebaute Katalog muss
für eigene Ergänzungen nicht geändert werden. Die Beispieldatei enthält nur eine
künstliche `.example`-Domain.
