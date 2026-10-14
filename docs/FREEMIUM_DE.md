# Account Compass Free und Pro

Account Compass wird als datenschutzfreundliches Freemium-Produkt vorbereitet.
Dieses Repository enthält aktuell **Account Compass Free**. Diese Edition ist
vollständig nutzbar und lokal; sie benötigt weder Online-Konto, Zahlungsdaten noch
Telemetrie.

## Jetzt verfügbar: Free

- Lokale Account-Inventur mit dem Katalog aus 527 Anbietern.
- Lokaler Import von EML, mbox und Maildir sowie ausdrücklich freigegebener,
  nur lesender IMAP-Zugriff.
- Account-Prüfung, Sicherheitschecklisten und passwortfreier Bitwarden-
  Metadatenexport.
- Deutsche und englische Oberfläche.

## Pro-Edition in Entwicklung

Das Dashboard nennt drei Pro-Funktionen in Entwicklung: lokalen verschlüsselten
Sicherungs- und Wiederherstellungsablauf, geplante lokale Prüferinnerungen und
erweiterte persönliche Sicherheitsberichte. Sie sind in dieser Version weder
implementiert noch kaufbar. Die Anwendung enthält eine signierte Offline-
Lizenzgrundlage, aber dieser Standard-Build enthält keinen Herausgeber-
Öffentlichkeitsschlüssel und kann Pro nicht aktivieren. Free wird nicht durch
künstliche Testlimits eingeschränkt.

## Produktgrenzen

- Passwörter werden in Bitwarden erzeugt und gespeichert, niemals in Account
  Compass.
- Mailinhalte, IMAP-Geheimnisse, Zahlungsdaten und Bitwarden-Tresordaten werden
  nicht an einen Produktdienst gesendet. Eine optionale bereits entsperrte
  Bitwarden-CLI kann ausdrücklich ausgewählte passwortfreie Einträge lokal
  erstellen, ohne bestehende Einträge zu lesen.
- Ein späterer Kauf muss über einen getrennten Checkout des Herausgebers laufen.
  Zahlungsgeheimnisse gehören nicht in die Desktop-App oder dieses Repository.
- Eine spätere Pro-Lizenz benötigt unabhängig geprüfte, signierte Offline-
  Verifizierung, bevor kostenpflichtige Funktionen durchgesetzt werden. Ein
  lokal veränderbarer Schalter ist keine gültige Zahlungs- oder Lizenzkontrolle.
- Das umgesetzte Lizenzformat und der Umgang mit Herausgeber-Schlüsseln stehen in
  [LICENSE_IMPLEMENTATION.md](LICENSE_IMPLEMENTATION.md).

## Vor dem Verkauf von Pro

Der Herausgeber muss Verkäuferidentität, Rechtsraum, Preis, Steuerabwicklung,
Widerrufs-/Erstattungsregelung, Supportkanal, kommerzielle Lizenz und
Zahlungsanbieter bestimmen. Erst danach die endgültigen Rechtstexte und einen
geprüften Checkout ergänzen. Siehe die
[Checkliste für die kommerzielle Veröffentlichung](COMMERCIAL_RELEASE.md).
