REGELN ZUR CODIERUNG
VERIFIZIERUNGSPFLICHTIGER ARZNEIMITTEL
IM DEUTSCHEN MARKT
Gemäß der EU-Fälschungsschutzrichtlinie 2011/62/EU
und der delegierten Verordnung (EU) 2016/161
Codierung mittels Data Matrix Code mit den Produktcodes PPN oder NTIN
und den weiteren Datenelementen
Automatische Identifikation von Arzneimittelpackungen
in der pharmazeutischen Lieferkette
Version: 2.03 Ausgabedatum: 5. Mai 2017
ASC-Format GS1-Format
Seite 2 All contents copyright © securPharm e.V. | Deutsch V 2.03
Inhalt
1 Einleitung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
2 Anwendungsbereich . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
3 Technische Hinweise zur Verifizierung in Kurzform . . . . . . . . . . . . . . . . 6
3.1 Regeln zur Seriennummer. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
3.2 Datentransfer zum ACS-PU-System. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
4 Vereinbarungen zur Codierung . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
4.1 Allgemeines. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
4.2 Pharmacy Product Number (PPN) – Anwendung in Deutschland. . . . . . . . . . . . 8
4.3 National Trade Item Number (NTIN) – Anwendung in Deutschland . . . . . . . . . . 8
4.4 Codes und Dateninhalte auf Arzneimittelpackungen. . . . . . . . . . . . . . . . . . . . . . 9
4.5 Multi Market Packs. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
4.6 Klinikpackungen. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
5 Dateninhalte und Anforderungen . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
5.1 Datenbezeichner und Strukturen. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
5.2 Single Market Packs –
Datenelemente und zugehörige
Datenbezeichner. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
5.2.1 Produktcode. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
5.2.2 Seriennummer. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
5.2.3 Chargenbezeichnung. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
5.2.4 Verfalldatum. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
5.2.5 Weitere Datenelemente – Beispiel URL. . . . . . . . . . . . . . . . . . . . . . . . . . . 12
5.3 Multi Market Packs – Datenelemente und zugehörige Datenbezeichner. . . . . 13
5.3.1 Allgemeines. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
5.3.2 Landesspezifische Kennung im GS1-Format:. . . . . . . . . . . . . . . . . . . . . . 13
5.3.3 Landesspezifische Kennung im ASC-Format:. . . . . . . . . . . . . . . . . . . . . . 14
6 Kennzeichnung mit Code und Klartext . . . . . . . . . . . . . . . . . . . . . . . . . . 14
6.1 Symbologie. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
6.2 Matrixgröße. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
6.3 Codegröße und Ruhezone. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
6.4 Positionierung des Data Matrix Codes. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
6.5 Emblem zum Data Matrix Code. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
6.6 Klartextinformation. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
7 Qualitätsprüfung des Data Matrix Codes . . . . . . . . . . . . . . . . . . . . . . . . 17
8 Interoperabilität auf Basis von XML-Standards . . . . . . . . . . . . . . . . . . . 19
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 3
Anhang A
Übersicht und Referenz der Datenbezeichner . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20
Anhang B
Emblem zum Code . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
Anhang C
Interoperabilität auf der Basis von XML-Beschreibungen (informativ) . . . . . . . . . . . . . . 22
C.1 Allgemeines. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
C.2 Data-Format-Identifier (DFI). . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
C.3 XML-Knoten für Daten. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
C.4 Anwendung. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
C.5 Beispiele. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 24
Anhang D
Details zur Qualitätsprüfung des Data Matrix Codes . . . . . . . . . . . . . . . . . . . . . . . . . . 25
D.1 Allgemeines. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
D.2 Lesekontrolle. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
D.2.1 Manuelle Lesekontrollen. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
D.2.2 Inline-Kontrolle. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
D.3 Messung gemäß ISO/IEC 15415. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
D.4 Messbedingungen nach ISO/IEC 15415. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
D.5 Parameter zur Druckqualität . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26
Anhang E
Glossar . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28
Anhang F
Bibliography . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
F.1 Normen. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
F.2 Referenz zu Spezifikationen. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
Anhang G
Dokumentenhistorie . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
Impressum . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 36
Seite 4 All contents copyright © securPharm e.V. | Deutsch V 2.03
1 Einleitung
Gemäß Art. 54a Abs. 1 der durch die sog. EU-Fälschungsschutzrichtlinie 2011/62/EU (FMD) geänderten
Richtlinie 2001/83/EG sind verschreibungspflichtige
Arzneimittel grundsätzlich mit Sicherheitsmerkmalen zu
kennzeichnen, die insbesondere eine Überprüfung ihrer
Echtheit und die Identifizierung von Einzelpackungen ermöglichen. Die Mitgliedstaaten müssen dann gemäß Art.
2 Abs. 2 lit. b) der FMD diese Vorschriften zur Kennzeichnung mit den Sicherheitsmerkmalen drei Jahre nach
Veröffentlichung der delegierten Rechtsakte anwenden.
Die Einzelheiten hinsichtlich der Eigenschaften und technischen Spezifikationen des individuellen Erkennungsmerkmals für die Sicherheitsmerkmale sind in der delegierten Verordnung (EU) 2016/161 der Kommission vom
2. Oktober 2015 festgelegt und am 9. Februar 2016 im
Europäischen Amtsblatt veröffentlicht. Die Akteure der legalen pharmazeutischen Lieferkette in Deutschland müssen nun diese Vorgaben bis spätestens zum 9.2.2019
umsetzen. Ab diesem Stichtag dürfen keine von der Fälschungsschutzrichtlinie betroffenen Produkte mehr ohne
die Sicherheitsmerkmale in Verkehr gebracht werden.
Diese Verordnung sieht ein System vor, das die
Identifizierung und die Feststellung der Echtheit
von Arzneimitteln durch eine End-to-end-Verifizierung aller Arzneimittel, die die Sicherheitsmerkmale
tragen, gewährleistet.
Vor diesem Hintergrund haben die nachfolgend genannten Stakeholder den Verein „securPharm e.V.“ gegründet,
um frühzeitig ein Konzept zur betrieblichen Umsetzung
der Verifizierungsvorschriften zu entwickeln, das System
aufzubauen, zu erproben und kontinuierlich zu verbessern:
• ABDA – Bundesvereinigung Deutscher Apothekerverbände e.V. (Federal Union of German Associations of Pharmacists)
• Avoxa – Mediengruppe Deutscher Apotheker
GmbH
• Bundesverband der Arzneimittel-Hersteller e.V.
(BAH) (German Medicines Manufacturers‘ Association)
• Bundesverband der Pharmazeutischen Industrie e.V. (BPI) (German Pharmaceutical Industry Association)
• IFA Informationsstelle für Arzneispezialitäten
GmbH (German Issuing Agency for Pharmacy Products)
• PHAGRO | Bundesverband des Pharmazeutischen Großhandels e.V. (Association of Pharmaceutical Wholesalers)
• Verband Forschender Arzneimittelhersteller e.V.
(vfa) (Association of Research-Based Pharmaceutical Companies)
Abbildung 1: System zur Verifizierung
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 5
securPharm basiert auf einem Konzept, bei dem durch
den systemtechnischen Ansatz die Akteure Herr ihrer
Daten (siehe Abbildung 1) bleiben. Die pharmazeutischen Unternehmen (pU) laden ihre packungsbezogenen Daten in das Datenbanksystem der pharmazeutischen Industrie (ACS-PU-System). Zum Betrieb des
ACS-PU-Systems haben die Verbände BAH, BPI und
vfa die ACS PharmaProtect GmbH als Betreibergesellschaft gegründet. Verifikationsanfragen der Apotheken
werden über ein zentrales Apotheken-System gebündelt
und anonymisiert an das ACS-PU-System gerichtet. Das
Apotheken-System wird von der Avoxa – Mediengruppe
Deutscher Apotheker GmbH betrieben. Der Großhandel
nimmt seine Verifikationen ebenfalls über das zentrale
Apotheken-System vor. Diese Systemtrennung und die
Anonymisierung der Verifikationsanfragen im System der
Apotheken stellt die gegenseitige Vertraulichkeit der Daten vollständig sicher und belässt die Verantwortlichkeit
in den Händen der Prozessbetreiber. Damit sind auch
für die Effizienz der Organisationskosten, der Investitionen und Betriebskosten günstigste Voraussetzungen
geschaffen.
Seit 2013 können pharmazeutische Unternehmen securPharm nutzen und ihre eigenen Prozesse trainieren. Mit
securPharm ist das nationale Verifikationssystem (National Medicines Verification System – NMVS) für Deutschland geschaffen. Es ist als solches Partner im Rahmen
des sicheren Netzwerkes in Europa der European Medicines Verification Organisation (EMVO).
Als Kernelement zur Verifizierung sieht die FMD vor,
dass jede Packung mit einem sogenannten individuellen Erkennungsmerkmals (Unique Identifier) zu
versehen ist. Um die Identifikation des individuellen
Erkennungsmerkmals auf den Arzneimittelpackungen sicherzustellen, sind in dieser Spezifikation die
Vorgaben des Gesetzgebers wiedergegeben und
mit den notwendigen technischen Details ergänzt.
Der Herausgeber weist daraufhin, dass die vorliegenden
„Regeln zur Codierung“ auf Grundlage des aktuellen
Standes der Erkenntnisse zum Zeitpunkt der Drucklegung nach bestem Wissen erstellt wurden.
Aufgrund rechtlicher und technischer Fragen und der ggf.
erforderlichen Anpassung sozialrechtlicher oder anderer
Vorgaben können Änderungen und Anpassungen für die
Zukunft jedoch nicht ausgeschlossen werden und müssen daher ausdrücklich vorbehalten bleiben.
Weitere Informationen zu securPharm finden sich unter
www.securPharm.de.
2 Anwendungsbereich
Da sich die Verifikation in einem Systemverbund zwischen
verschiedenen Akteuren in einem sog. offenen System
abspielt, ist die gegenseitige technische Abstimmung die
zwingende Voraussetzung für den reibungslosen Ablauf.
Zu diesem Zweck beschreiben die vorliegenden Codierregeln für kennzeichnungspflichtige Arzneimittel, die in
den deutschen Markt in Verkehr gebracht werden, die
technischen Spezifikationen des individuellen Erkennungsmerkmals (Unique Identifier). Anzuwenden ist es
von den pUs, die die Arzneimittel kennzeichnen sowie
den Akteuren, die die Überprüfung des individuellen Erkennungsmerkmals vorzunehmen haben. Letztere sind
in erster Linie die Apotheken und der Großhandel. Deren
Systemlieferanten haben diese Spezifikation zu beachten
und umzusetzen.
In diesem Dokument finden sich die besonderen Ausprägungen des für den deutschen Markt festgelegten
Produktcodes. Im Detail werden die Codierung, Codeinhalt, Codegröße und Druckqualität sowie die damit
verbundene Kennzeichnung der Arzneimittelpackungen
beschrieben.
Anmerkung: Die hier festgelegten Regeln weichen in einigen Punkten von den derzeitigen Spezifikationen der
GS1 ab, sind aber in jedem Fall vorrangig anzuwenden.
Die Transportlogistik und die Aggregation der Handelseinheit sind kein Bestandteil dieses Regelwerks. Die im
Rahmen der Codierung für das securPharm Projekt angewandten ISO Normen erlauben dem Anwender, die
Daten und das System der Pharmacy Product Number
(PPN) oder der National Trade Item Number (NTIN) in
übergeordnete standardisierte Systeme zur Transportlogistik und Aggregation einzubinden (ISO 15394).
Diese Codierregeln beschreiben ebenfalls nicht:
• die im Rahmen der Verifizierung notwendigen Prozesse zur Informationstechnik (IT) und
• die von der FMD geforderte Vorrichtung gegen Manipulation (auch anti-tampering device genannt).
Seite 6 All contents copyright © securPharm e.V. | Deutsch V 2.03
3 Technische Hinweise zur Verifizierung in Kurzform
3.1 Regeln zur Seriennummer
Die zur Verifizierung erforderliche Seriennummer ist eine
numerische oder alphanumerische Folge von höchstens
20 Zeichen, die der pharmazeutische Unternehmer (pU)
generiert. Um es einem Fälscher möglichst schwer zu
machen, vom pU vergebene Seriennummern zu erraten
oder zu reproduzieren, sind diese durch einen deterministischen oder nicht-deterministischen Randomisierungsalgorithmus zu generieren. Die Wahrscheinlichkeit,
dass die Seriennummer abgeleitet werden kann, muss
in jedem Fall geringer als 1:10.000 sein. Zudem hat die
randomisierte Seriennummer in Kombination mit dem
auf der PZN basierenden Produktcode für jede Arzneimittelpackung während eines Zeitraums von mindestens
einem Jahr ab dem Verfalldatum der Packung oder mindestens fünf Jahren ab dem Inverkehrbringen des Arzneimittels (maßgebend ist der jeweils längere Zeitraum)
individuell zu sein.
Die Wiederverwendung von Seriennummern stellt eine
potentielle Fehlerquelle dar und wird daher nicht empfohlen.
3.2 Datentransfer zum ACS-PU-System
Für den Verifizierungsprozess übermittelt der pU seine
Packungsdaten an das ACS-PU-System. Diese beinhalten folgende datentechnische Schlüsselelemente:
• Produktcode (im Format einer PPN oder NTIN)
• Seriennummer
• Chargenbezeichnung
• Verfalldatum
Neben den o.a. Schlüsselelementen hat der pU weitere
Informationen mit zu übertragen, z.B. gem. Art. 33 Abs.
2 lit. f) der delegierten Verordnung den Hersteller, der die
Sicherheitsmerkmale aufgebracht hat.
Notwendige Produktstammdaten werden mit Bezug auf
die entsprechende PZN über die Informationsdienste der
IFA derzeit direkt an das ACS-PU-System übermittelt.1
Der Verifizierungsprozess steht für die Produkte zur Verfügung, die der pU der IFA über den Änderungsdienst
gemeldet hat. Von dieser Meldung ist auch der Upload
der Produktstammdaten vom IFA-System an das ACSPU-System abhängig.
Vorrausetzung zur Teilnahme am nationalen Verifizierungssystem ist der mit ACS abzuschließende Nutzungsvertrag. Die frühzeitige Anbindung ist wichtig, um die Unternehmensprozesse zu trainieren und mögliche interne
Fehlerquellen zu identifizieren und auszuschließen.2
Nähere Informationen zur organisatorischen und technischen Anbindung an das ASC-PU-System finden sich
unter: http://www.pharmaprotect.de/de/.
1 Die Ausführung zu den Produktstammdaten gilt zunächst für
die direkte Anbindung an das nationale System von ACS. Das
Konzept wird überarbeitet, sobald die Details zur Anbindung an
den HUB vorliegen.
2 Für Unternehmen, die bisher mit der Umstellung auf die neuen Sicherheitsmerkmale noch am Anfang stehen, ist eine frühzeitige Anbindung ebenfalls sehr zu empfehlen. Sie profitieren
auf diese Weise vom Erfahrungsaustausch mit anderen Marktteilnehmern sowie von der Unterstützung durch die Experten von
securPharm und ACS.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 7
4 Vereinbarungen zur Codierung
4.1 Allgemeines
Gemäß Art. 4 der delegierten Verordnung umfasst das
individuelle Erkennungsmerkmal die folgenden Datenelemente:
• Produktcode
• Seriennummer
• Chargenbezeichnung
• Verfalldatum
Als weiteres Element ist in Art. 4 noch die nationale Kostenerstattungsnummer erwähnt. Diese ist für Arzneimittel,
die für den deutschen Markt bestimmt sind, in Form der
PZN bereits im Produktcode enthalten (siehe Kapitel 4.2)
und braucht deshalb gemäß Art. 4 lit. e) der delegierten
Verordnung nicht mehr als fünftes Element extra aufgeführt zu werden.
Die Codierung erfolgt im Data Matrix Code (DMC) nach
ISO/IEC 16022 (siehe Kapitel 6.1) und der Datenstruktur
und Syntax gemäß ISO/IEC 15418 sowie ISO/IEC 15434
(siehe Kapitel 5).
Damit ist die Maschinenlesbarkeit dieser Datenelemente
gegeben und die technische Voraussetzung für die Umsetzung der EU-Richtlinie zum Schutz vor Arzneimittelfälschungen sowie der weiteren gesetzlichen Auflagen
zur Verifizierung von Arzneimittelpackungen geschaffen.
Zugleich sind damit die Anforderungen aus Art. 5 „Träger
des individuellen Erkennungsmerkmals“ der delegierten
Verordnung erfüllt.
Zur Erfüllung der Anforderungen von Art. 4 lit. d) der delegierten Verordnung wird ein europaweit eindeutiger Produktcode benötigt. Bei in Deutschland verkehrsfähigen
Arzneimittel wird als Produktcode die Pharmacy Product
Number (PPN) zur Verifizierung herangezogen. Im Data
Matrix Code kann der Produktcode entweder im Format
der PPN oder der National Trade Item Number (NTIN) dargestellt werden. Beide Formate generieren sich jeweils
aus der 8-stelligen PZN. Der pharmazeutische Hersteller
kann sich zwischen den beiden genannten Formaten des
Produktcodes frei entscheiden.
Existierende Datenbanken und Softwaresysteme können
algorithmisch aus der PPN oder der NTIN eine PZN generieren und umgekehrt aus der PZN eine PPN oder NTIN
erzeugen.
Für den Handel bleibt die PZN die relevante Artikelnummer und wird wie bisher für die Kostenerstattung und die
arzneimittelrechtlichen Belange herangezogen. Somit
werden die existierenden Prozesse unverändert beibehalten.
Die Interoperabilität mit anderen Nummernsystemen,
z.B. GTIN (GS1 als zuständige Issuing Agency) oder
HIBC (EHIBCC als zuständige Issuing Agency), ist durch
die gemeinsame Basis der internationalen Normen zuverlässig gewährleistet. In den zwei folgenden Kapiteln
sind in Kurzform die Eigenschaften und die Methoden zur
Generierung der PPN und NTIN beschrieben.
Seite 8 All contents copyright © securPharm e.V. | Deutsch V 2.03
4.2 Pharmacy Product Number (PPN) –
Anwendung in Deutschland
Die PZN wird, wie folgt dargestellt, in das weltweit
eindeutige Format der PPN eingebettet.
Pharmacy Product Number (PPN)
11 12345678 42
Product Registration PZN Check-Digits PPN
Agency Code for PZN
Abbildung 2: Generierung der PPN
Die PPN besteht aus drei Teilen, die farblich rot, blau und
grün hervorgehoben sind. Die „11“ steht für einen Product Registration Agency Code (PRA-Code oder PRAC).
Dieser Code wird von der IFA verwaltet und vergeben.
Die „11“ ist für die PZN reserviert. Nach der „11“ folgt,
in blau dargestellt, die nationale Artikelnummer. Dabei
handelt es sich um die unveränderte PZN (PZN8). Die
darauf folgenden Ziffern (im Bild grün dargestellt) bilden
die zweistellige, errechnete Prüfziffer über das komplette
Datenfeld (einschließlich der „11“). Mit der im Beispiel
dargestellten PZN ergibt sich der Wert „42“.
Detaillierte Informationen zur PPN und zum PPN-Generator finden sich unter http://www.ifaffm.de/de/ifacodingsystem/von-pzn-zu-ppn.html sowie in dem Dokument „Data Matrix Code auf Handelspackungen“
unter http://www.ifaffm.de/de/ifa-codingsystem/datamatrix-handelspackungen.html.
4.3 National Trade Item Number (NTIN) –
Anwendung in Deutschland
Die PZN wird, wie folgt dargestellt, in das weltweit
eindeutige Format der NTIN eingebettet.
National Trade Item Number (NTIN)
0 4150 12345678 2

GS1-Prefix for PZN PZN Check-Digit NTIN
Abbildung 3: Generierung der NTIN
Die NTIN besteht aus drei Teilen, die farblich rot, blau und
grün hervorgehoben sind. Die „4150“ ist der von der GS1
Deutschland vergebene Präfix für die PZN. Danach folgt,
in blau dargestellt, die unveränderte PZN (PZN8). Die
letzte Ziffer (im Bild grün dargestellt) bildet die Prüfziffer
über das komplette Datenfeld. Detaillierte Informationen
zur NTIN und zur Generierung der Prüfziffer sind in
dem NTIN-Leitfaden der GS1 zu finden (https://www.
gs1-germany.de/fileadmin/gs1/basis_informationen/
kennzeichnung_von_pharmazeutika_in_deutschland.
pdf).
Zusätzlich muss durch Voranstellen einer „0“ die NTIN,
wie oben dargestellt, für diese Verwendung auf ein
14-stelliges Format gebracht werden.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 9
4.4 Codes und Dateninhalte auf Arzneimittelpackungen
Bis auf weiteres bleiben die Codierungen der PZN im Code 39 und auch andere Codierungen, wie z.B. der EAN-13 auf
den Handelspackungen erhalten.1
 Dies sichert die Beibehaltung der etablierten Prozesse.
Bei verifizierungspflichtigen Arzneimitteln muss der Data Matrix Code zusätzlich aufgebracht werden. Bei allen anderen
Produkten ist die Aufbringung optional. Ergänzend zur PPN/NTIN können weitere Daten im Data Matrix Code enthalten
sein. Eine Seriennummer ist allerdings bei nicht verifizierungspflichtigen Arzneimittel nicht erlaubt.
Im Folgenden sind die grundsätzlichen Varianten beschrieben:
Code 391 Data Matrix Code
PZN PPN/NTIN SN LOT EXP
Verifizierungspflichtiges Arzneimittel √ √ √ √ √
Nicht verifizierungspflichtiges Arzneimittel √ √ nicht
erlaubt optional optional
Abbildung 4: Varianten in der Codierung
1 Nach dem Fünften Buch Sozialgesetzbuch (SGB V) ist die Angabe der PZN im PZN-Code zunächst weiterhin obligatorisch.
Die delegierte Verordnung lässt es zu, weitere ein- oder zweidimensionale Codes auf die Packung aufzubringen, sofern
diese nicht das individuelle Erkennungsmerkmal enthalten, das zur Überprüfung der Echtheit oder der Identität dient.
Somit kann es im Rahmen der individuellen Zulassung möglich sein, Codes aufzubringen, die weitere Informationen
enthalten oder auf andere Quellen verweisen, wie z.B. einen Uniform Resource Locator (URL). Weitere Codes beeinträchtigen möglicherweise aber die Prozesssicherheit und sollten auf das notwendigste beschränkt sein.
4.5 Multi Market Packs
Multi Market Packs (MMP) sind Handelspackungen, die
in einer bestimmten Aufmachung in mehreren Ländern
abgabefähig sind. Sie tragen in der „blue box“ mehrere
nationale Artikelnummern für Erstattungszwecke und warenwirtschaftlichen Belange sowie weitere verschiedene
länderspezifische Informationen.
Für verifizierungspflichtige MMP ist es zwingend, einen
Produktcode zu definieren, der übergreifend für alle Länder herangezogen wird, in denen das infrage stehende
Arzneimittel verifizierungspflichtig ist. Dieser Produktcode wird mit der zugehörigen Seriennummer und den
anderen Informationen über den HUB in alle nationalen
Verifizierungssysteme hochgeladen. Bei der Abgabe des
Arzneimittels wird der Status der betreffenden Packung
wiederum über den HUB in allen betroffenen nationalen
Verifizierungssystemen synchronisiert.
Jedes Land legt fest, welche nationale Nummer neben
dem Produktcode in den Data Matrix Code mit aufzunehmen ist. Bei Arzneimitteln, die für den deutschen Markt bestimmt sind, ist die PZN verpflichtend in den Data Matrix
Code aufzunehmen. Entweder direkt im Produktcode wie
in Kapitel 4 beschrieben oder als weiteres Element, falls
der Produktcode einem anderen Land zugeordnet ist.
Die Details zur Codierung sind in Kapitel 5.3 beschrieben.
Abbildung 5: Multi Market Pack
Seite 10 All contents copyright © securPharm e.V. | Deutsch V 2.03
4.6 Klinikpackungen
Klinikpackungen werden grundsätzlich wie apothekenübliche Handelspackungen codiert. Eine Besonderheit stellen die
Klinikpackungen dar, die aus Klinikbausteinen1
 bestehen. Bei dieser Variante verkörpert die Klinikpackung und nicht der
Klinikbaustein die Handelspackung. Somit ist das individuelle Erkennungsmerkmal auf die Klinikpackung und nicht auf
den Klinikbaustein aufzubringen.
Aus z.B. logistischen Gründen dürfen die Klinikbausteine zwar einen DMC tragen, allerdings dürfen die Datenelemente
nicht an das ACS-PU-System übermittelt bzw. zur Verifizierung herangezogen werden (siehe untenstehende Tabelle).
Apothekenübliche Handelspackung
Klinikpackung Klinikpackung
mit sog. Klinikbausteinen1
Packungsinhalt Einzelobjekte
(Blister, Dragees,
Fläschchen , …)
Einzelobjekte
(Blister, Dragees,
Fläschchen , …)
Einzelne Packungen, die sog. Klinikbausteine, die in einem Bündel oder einer anderen
Umverpackung zu einer Klinikpackung
zusammengeführt sind.
IFA-Artikeltyp Standardware Klinikpackung Klinikpackung Klinikbaustein
PZN im Code 39
(Strichcode) √ √ √ √
Data Matrix Code
- Dateninhalt
obligatorisch
- Produktcode
- Seriennummer
- Chargenbez.
- Verfalldatum
obligatorisch
- Produktcode
- Seriennummer
- Chargenbez.
- Verfalldatum
obligatorisch
- Produktcode
- Seriennummer
- Chargenbez.
- Verfalldatum
optional
- Produktcode
- Chargenbez.
- Verfalldatum
ACS-PU-System NTIN/PPN
SN
LOT
EXP
NTIN/PPN
SN
LOT
EXP
NTIN/PPN
SN
LOT
EXP
–
Objekt zur
Verifizierung √ √ √ –
Abbildung 6: Übersicht Klinikpackungen
1 Als Klinikbaustein wird eine der Handelspackung in der Aufmachung gleiche Packung bezeichnet, die allerdings einzeln nicht
verkaufsfähig ist. Dem Klinikbaustein ist eine PZN zur Identifizierung zugeordnet. Die PZN des Klinikbausteins verweist auf die PZN
der Klinikpackung. Aus in einem Bündel oder einer anderen Umverpackung zusammengefassten Klinikbausteinen entstehen Klinikpackungen, denen die für den Handel relevante PZN zugeordnet ist.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 11
5 Dateninhalte und Anforderungen
5.1 Datenbezeichner und Strukturen
In diesem Kapitel sind die zu verwendenden Datenbezeichner und die Ausprägungen der Datenelemente
definiert. Zur Verwendung kommen die Datenbezeichner
gemäß der internationalen Norm ISO/IEC 15418 (diese
verweist auf die ANSI MH10.8.2; Data Identifier and
Application Identifier Standard). Dabei nutzt die IFA die
ASC MH10 Data Identifier (DI) und die GS1 die Application Identifier (AI).
Die Normen lassen die Ausprägung der Datenelemente
in der Regel offen. Deshalb sind in diesem Dokument, für
alle Marktteilnehmer verbindlich, der jeweilige Datentyp,
die Datenlänge und der Zeichenvorrat definiert (siehe Kapitel 5.2). Für Strukturen und Datenbezeichner ist eine
der beiden folgenden Varianten zulässig:
A Struktur im Format 06 gemäß ISO/IEC 15434 und
ASC MH10 Data Identifier (DI) gemäß ISO/IEC
15418 (ANSI MH10.8.2) Details siehe Spezifikation
der IFA: http://www.ifaffm.de/de/ifa-codingsystem/
data-matrix-handelspackungen.html (Dokument
„Data Matrix Code auf Handelspackungen“)
B Strukturkennzeichen „FNC1“ und Application
Identifier (AI) gemäß ISO/IEC 15418 Details siehe
Spezifikation der GS1: https://www.gs1-germany.
de/loesung-fuer-faelschungssichere-arzneien/
Die einsetzbaren Datenbezeichner sowie die zulässigen Datentypen, Zeichensätze und Datenlängen
der zu codierenden Daten sind in Anhang A zusammenfassend dargestellt.
Nicht in dieser Spezifikation verwendete Datenbezeichner, die jedoch der Syntax der ANSI MH10.8.2. folgen,
sollen in den Applikationen korrekt ausgegeben werden
und zu definierten Zuständen führen.
Der Lesevorgang und die damit verbundene Datenerfassung dürfen dadurch nicht gefährdet werden.
Die spezifizierten Datenstrukturen dürfen durch solche Erweiterungen nicht verletzt werden.
Sollten für die Marktteilnehmer weitere Datenbezeichner
zur gemeinsamen Nutzung herangezogen werden, so wird
securPharm diese ergänzend zu den in Kapitel 5.2 beschriebenen Datenbezeichnern in die Codierregeln aufnehmen und deren Anwendung eindeutig beschreiben.
5.2 Single Market Packs –
Datenelemente und zugehörige
Datenbezeichner
5.2.1 Produktcode
• Data Identifier (DI): „9N“
• Application Identifier (AI): „01“
Zur Produktidentifikation wird der Produktcode herangezogen, entweder in Form der Pharmacy Product Number
(PPN) oder der National Trade Item Number (NTIN). Der
Produktcode ist das führende Datenelement im DMC,
alle weiteren Datenelemente beziehen sich auf diesen. Im
Produktcode ist jeweils die PZN enthalten und kann daraus extrahiert werden (siehe Kapitel 4.2 und Kapitel 4.3).
Es muss die auf 8 Stellen erweiterte PZN verwendet werden.
Beispiel:
Format DI
AI Daten
ASC 9N 110375286414
GS1 01 04150037528643
5.2.2 Seriennummer
• Data Identifier (DI): „S“
• Application Identifier (AI): „21”
Die Seriennummer wird vom pharmazeutischen Unternehmer generiert und bildet das entsprechende Datenelement des individuellen Erkennungsmerkmals. Sie ist
für den Verifizierungsprozess obligatorisch. Bei nicht
verifizierungspflichtigen Arzneimitteln darf die Seriennummer nicht aufgebracht werden.
Format DI
AI Daten
ASC S 12345ABCDEF98765
GS1 21 12345ABCDEF98765
Die verwendbaren Zeichen sind im Anhang A beschrieben.
Seite 12 All contents copyright © securPharm e.V. | Deutsch V 2.03
5.2.3 Chargenbezeichnung
• Data Identifier (DI): „1T“
• Application Identifier (AI): „10“
Die Chargenbezeichnung wird vom pharmazeutischen
Unternehmer generiert und bildet somit das entsprechende Datenelement für den DMC. Zur Abgrenzung
von Teil-/Unterchargen können definierte Sonderzeichen
verwendet werden (siehe Anhang A).
Beispiel:
Format DI
AI Daten
ASC 1T 12345ABCD
GS1 10 12345ABCD
5.2.4 Verfalldatum
• Data Identifier (DI): „D“
• Application Identifier (AI): „17“
Das Verfalldatum wird vom pharmazeutischen Unternehmer generiert und bildet somit das entsprechende
Datenelement für den DMC.
Das Verfalldatum hat das Format „YYMMDD“
YY = zweistellige Jahreszahl
Da das Verfalldatum ausschließlich in der Zukunft liegt,
handelt es sich um Datumsangaben für das 21. Jahrhundert (2000–2099).
MM = Numerische Monatsangabe (01–12)
DD = Tag
a) Verfalldatum mit Tages-, Monats- und Jahresangabe
(DD = 01–31)
b) Verfalldatum mit Monats- und Jahresangabe
(DD = 00)
Beispiel: Verfalldatum Juni 2021
Format DI
AI Daten
ASC D 210600
GS1 17 210600
Dieses Beispiel stellt die vom AMG vorgegebene Datumsangabe dar.
Beispiel: Verfalldatum 30. Juni 2021
Format DI
AI Daten
ASC D 210630
GS1 17 210630
Dieses Beispiel stellt die Möglichkeit einer tagesgenauen
Datumsangabe dar.
Anmerkung: In der ANSI MH10.8.2 ist „D“ als Datum
allgemein definiert. Im Kontext der PPN ist das Datum „D“
zwangsweise das Verfalldatum. Bei anderen Datumsangaben, wie z.B. dem Produktionsdatum, sind andere
Datenbezeichner zu verwenden. Beim Produktionsdatum
wäre dies der DI „16D“ respektive der AI „11“.
5.2.5 Weitere Datenelemente – Beispiel URL
Zur Erfüllung der Vorgaben der delegierten Verordnung
sind die zuvor beschriebenen Datenelemente obligatorisch. Gemäß Art. 8 der Verordnung ist es erlaubt,
weitere Datenelemente aufzunehmen, soweit die zuständige Behörde dies gemäß Titel V der Richtlinie 2001/83/
EG bzw. § 10 Abs. 1, Satz 5 AMG gestattet.
So kann z.B. kann eine URL in den Code aufgenommen
werden:
Format DI
AI Daten
ASC 33L http://Beispiel.de
GS1 8200 http://Beispiel.de
Zu beachten ist, dass lange URLs den Code erheblich
vergrößern und entsprechend sich die Leserate verschlechtern kann.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 13
5.3 Multi Market Packs – Datenelemente und zugehörige Datenbezeichner
5.3.1 Allgemeines
Wie bei Single Market Packs enthält der Data Matrix Code
für Multi Market Packs ebenfalls das individuelle Erkennungsmerkmal, und der darin enthaltene Produktcode
wird zur Verifizierung herangezogen.
Eine Besonderheit ist, dass der Produktcode nicht zwingend die länderspezifische Identifizierung eines Arzneimittels vollständig abbildet und somit ergänzend zum
individuellen Erkennungsmerkmal weitere nationale Artikel- oder Erstattungsnummern im Code enthalten sein
können. Diese Ergänzungen sind gemäß den länderspezifischen Vorgaben und Notwendigkeiten des Handels
zusätzlich in den Data Matrix Code aufzunehmen. Dies
erlaubt es, mit einem Scan sowohl die zur Verifizierung
relevanten Daten, als auch die weiteren Nummern zur
länderspezifischen Identifizierung des Arzneimittels zu
erfassen.
Die Anwendersoftware extrahiert aus dem Code die dem
Warenwirtschaftssystem bekannten und notwendigen
Artikel- oder Erstattungsnummern zur Identifizierung und
zur weiteren Verarbeitung. Dieser Vorgang ist analog
zur gegenwärtigen Vorgehensweise beim sequentiellen
Scannen linearer Barcodes.
Die eindeutige Kennung des Produktcodes ist im
GS1-Format durch den AI (01) und im ASC-Format
durch den DI (9N) gegeben. Es wird empfohlen, den
Produktcode als erstes Datenelement zu codieren.
Bei Bedarf kann das höhere Datenvolumen mittels der
zusätzlich definierten Data Matrix Rechteckcodes bewältigt werden (siehe Kapitel 6.2).
Im Folgenden sind die Details zur Codierung der landesspezifischen Nummern zur Identifizierung beschrieben.
Alle anderen Spezifikationen aus Kapitel 5.1 und Kapitel
5.2 gelten auch für die MMP.
5.3.2 Landesspezifische Kennung im GS1-
Format:
Der Produktcode wird durch den AI (01) gekennzeichnet.
Die weiteren landesspezifischen Nummern zur Identifizierung des Arzneimittels werden durch die der s.g. NHRN
zugeordneten AI (71x) gekennzeichnet.
Für in Deutschland verkehrsfähige MMPs ist die deutsche
PZN mit dem AI (710) als NHRN und als Produktcode
die GTIN eines der anderen Märkte im Data Matrix Code
darzustellen.
Weitere Märkte sind im Data Matrix Code mit der jeweiligen NHRN zu kennzeichnen. Die landesspezifischen
Vorgaben sind zu berücksichtigen.
Beispiel MMP im GS1-Format (AIs)
Format AI Daten
GS1 01 1 08701234567896
GS1 21 1234567890ABCD
GS1 10 1234AB
GS1 17 210600
GS1 710 2 12345678
GS1 711 3 91234567
1 Produktcode (PC) GTIN
2 Weitere landesspezifische Produktidentifizierung mittels
NHRN, beispielhaft mit deutscher PZN
3 Weitere landesspezifische Produktidentifizierung mittels
NHRN, beispielhaft mit französischer CIP
Seite 14 All contents copyright © securPharm e.V. | Deutsch V 2.03
5.3.3 Landesspezifische Kennung im ASC-Format:
Der Produktcode wird durch den DI (9N) gekennzeichnet.
Sofern die weitere landesspezifische Nummer zur Identifizierung eines Arzneimittels, im Format einer GTIN oder
NTIN vorliegt, wird diese dem DI (8P) gekennzeichnet.
Bei mehreren landesspezifischen Nummern im Format
einer GTIN oder NTIN sind die zusätzlichen Datenbezeichner (8P) mehrfach im Code enthalten.
Beispiel MMP im ASC-Format (MH10 DIs)
Format DI Daten
ASC 9N 1 111234567842
ASC S 1234567890ABCD
ASC 1T 1234AB
ASC D 210600
ASC 8P 2 08701234567896
ASC 8P 3 03400912345676
Liegt das weitere landesspezifische Merkmal zur Identifizierung eines Produktes in einem von der GTIN oder
NTIN abweichenden Format vor, ist der dem jeweiligen
Format zugeordnete MH10 - DI gemäß ANSI-Standard
zu verwenden. Z.B. (25P) für HIBC.
Die Umsetzung dieser Variante ist mit der EMVO abzustimmen. Die technische Implementierung im HUB steht
bis dahin aus. Sobald die Implementierung erfolgt ist,
wird securPharm gesondert informieren.
1 Produktcode (PC) PPN, beispielhaft mit deutscher PZN „12345678“
2 Weitere landesspezifische Produktidentifizierung mittels GTIN
3 Weitere landesspezifische Produktidentifizierung mittels NTIN
6 Kennzeichnung mit Code und Klartext
6.1 Symbologie
Dieses Kapitel beschreibt die Codierung mit den Vorgaben für den Klartext und für die Elemente wie z.B. das
Emblem zum Code. Der verwendete Datenträger bzw. die
Symbologie ist der Data Matrix gemäß ISO/ IEC 16022.
Die Fehlerkorrektur erfolgt nach ECC200. Die anderen
Fehlerkorrekturmethoden (ECC000 bis ECC140) dürfen
nicht eingesetzt werden. Sofern immer eine gleichbleibende Matrixgröße gedruckt werden soll, sind ggf. Füllzeichen einzufügen.
6.2 Matrixgröße
Typischerweise soll die Matrixgröße von 26x26 bzw.
26x40 Modulen nicht überschritten werden. Kleinere Matrixgrößen sind erlaubt, sofern die Kapazität für die zu
kodierenden Daten ausreicht.
Je nach Packungslayout und den drucktechnischen
Voraussetzungen können quadratische oder rechteckige
DMCs verwendet werden. Bei den rechteckigen Codes
können auch die nach der DIN 16587:2015-11 zusätzlich spezifizierten Varianten herangezogen werden. Typische Matrixgrößen und deren Ausprägung finden sich in
folgenden Tabellen:
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 15
Quadratische Symbole
Matrixgröße Dimension (mm) Datenkapazität
Zeilen Spalten Typisch
X = 0,35
Min
X = 0,25
Max
X = 0,615
Numerisch Alphanumerisch
22 22 7,7 5,5 13,5 60 43
24 24 8,4 6,0 14,8 72 52
26 26 9,1 6,5 16,0 88 64
32 32 11,5 8,2 20,3 124 91
Rechteckige Symbole
Matrixgröße Dimension (mm) Datenkapazität
Zeilen Spalten Typisch
X = 0,35
Min
X = 0,25
Max
X = 0,615
Numerisch Alphanumerisch
16 36 5,6 x 12,9 4 x 9,2 9,8 x 22,7 64 46
16 48 5,6 x 17,1 4 x 12,2 9,8 x 30,1 98 72
24 48 8,4 x 17,1 6,0 x 12,2 14,8 x 30,1 160 118
26 48 9,1 x 17,1 6,5 x 12,2 16,0 x 30,1 180 133
X = Modulgröße in mm
Die Codes in den letzten zwei Zeilen der Tabelle „Rechteckige Symbole“ stammen aus der DIN 16587:2015-11 Information technology – Automatic identification and data capture techniques – Data Matrix Rectangular Extension. Die
Aufnahme dieser und weiterer rechteckiger Matrixgrößen in die ISO-Standards ist beantragt. Zu beachten ist, dass diese
Varianten des Data Matrix Codes bei den Verifizierungsstellen zum Zeitpunkt der Herausgabe dieser Spezifikation noch
nicht lesbar sind. Die Verifizierungsstellen haben die Umstellung sukzessive vorzunehmen und müssen spätestens zum
Zeitpunkt der gesetzlichen Verpflichtung in der Lage sein, diese Codes zu lesen.
6.3 Codegröße und Ruhezone
Die Modulgröße des Codes darf zwischen 0,25 und 0,615
mm variieren. Die technischen Eigenschaften der eingesetzten Scanner müssen auf diesen Bereich der Modulgrößen abgestimmt sein. Innerhalb dieses Bereiches dürfen die Modulgrößen unter Beachtung der Druckqualität
(siehe Kapitel 7) sowie der einzusetzenden Drucksysteme beliebig skaliert werden.
Mit der Modulgröße ist die Größe einer Matrixzelle gemeint (siehe Kapitel 6.2). Typische Modulgrößen liegen
zwischen 0,33 und 0,45 mm.
Die an den Code angrenzenden Flächen sind von weiterer Bedruckung freizuhalten. Zur Gewährleistung einer
akzeptablen Erstleserate wird für diese Anwendung ein
Abstand von mindestens drei Modulen festgelegt.
Seite 16 All contents copyright © securPharm e.V. | Deutsch V 2.03
6.4 Positionierung des Data Matrix
Codes
Für die Positionierung werden keine besonderen Festlegungen getroffen. Die Position bestimmt der Hersteller
aufgrund des Packungslayouts und der Gegebenheiten
des Bedruckens.
Das trifft auch für zentral zugelassene Arzneimittel zu, wobei der DMC außerhalb der „blue box“ aufzubringen ist.
6.5 Emblem zum Data Matrix Code
Das Emblem „PPN“ am Data Matrix Code weist die Verifizierungsstellen auf den Code hin, der zum maschinellen
Erfassen des Produktcodes und der weiteren Daten herangezogen wird, unabhängig vom Format der PZN im
DMC. Als Emblem wird „PPN“ solange beibehalten, bis
auf internationaler Ebene eine andere einheitliche Kennzeichnung festgelegt wird.
Abbildung 7: Emblem zum Code
Das Emblem kann in einer Übergangsphase entfallen.
Somit hat der pharmazeutische Unternehmer mehr Freiheiten bei den Umstellungsprozessen.
Zwingend aufzubringen ist es bei den Packungen, die
einen zweiten 2D-Code tragen.
Es sind verschiedene Varianten und Details zur graphischen Gestaltung des Emblems möglich (siehe Anhang
B).
Das Emblem kann sowohl im Primär- als auch im Inlinedruck aufgebracht werden. Die minimalen Abstände zum
Code (Ruhezonen) sind zu beachten.
6.6 Klartextinformation
Die PZN ist das Schlüsselelement der Verkaufspackung.
Nach den derzeit geltenden gesetzlichen Regeln muss
die PZN in Klarschrift mit dem Code 39 aufgebracht werden (siehe Spezifikation zur PZN http://www.ifaffm.de/de/
ifa-codingsystem/codierung-pzn-code_39.html).
Pharmazeutische Unternehmer müssen zukünftig neben
den Elementen PZN, Chargenbezeichnung und Verfalldatum den Produktcode und die Seriennummer in einem
vom Menschen lesbaren Format auf die Verpackung aufbringen. Zur Sicherstellung der Lesbarkeit sind die Ausführungen der „Guideline on the Readability of the Label
and Package Leaflet of Medicinal Products for Human
Use“ (sog. EU Readability Guideline) zu beachten.
Produktcode und Seriennummer:
Sofern es die Abmessungen der Verpackung zulassen,
befinden sich die Klartextinformation des Produktcodes
und der Seriennummer neben dem zweidimensionalen
Code, der das individuelle Erkennungsmerkmal enthält.
Werden der Produktcode und die Seriennummer in zwei
Zeilen untereinandergeschrieben, dann ist in der ersten
Zeile der Produktcode und in der zweiten die Seriennummer auszugeben.
Als Produktcode ist die im Code enthaltene PPN oder
NTIN heranzuziehen. Zur Kennzeichnung wird die Kurzbezeichnung „PC: “ vorangestellt.1
 Da der Produktcode
für die jeweilige Packungsaufmachung fix ist, kann dieser
auch im Primärdruck aufgebracht werden.
Der Seriennummer ist die Kurzbezeichnung „SN: “ voranzustellen.1
Ausnahmen gemäß der delegierten Verordnung:
Wenn die Summe der beiden längsten Abmessungen der
Verpackung 10 Zentimeter oder weniger beträgt, kann die
klarschriftliche Darstellung des Produktcodes sowie der
Seriennummer entfallen.
1 Leerzeichen nach dem Doppelpunkt beachten.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 17
Chargenbezeichnung und Verfalldatum:
Für die Klartextinformation der Chargenbezeichnung
und des Verfalldatums gelten die arzneimittelrechtlich
vorgegebenen Anforderungen zur Kennzeichnung. Für
die Chargenbezeichnung ist die Abkürzung „Ch.-B.: “
zu wählen.1
Das Verfalldatum ist mit dem Hinweis „verwendbar bis “
zu versehen.2
 Bei Behältnissen von nicht mehr als 10 Milliliter Nennfüllmenge und bei Ampullen, die nur eine einzige Gebrauchseinheit enthalten, kann gemäß AMG eine
geeignete Abkürzung (wie z.B. „verw. bis “) verwendet
werden.2
Beispiel PPN:
Beispiel NTIN:
1 Leerzeichen nach dem Doppelpunkt beachten.
2 Leerzeichen nach dem „bis“ beachten.
7 Qualitätsprüfung des Data
Matrix Codes
Grundvoraussetzung für einen nutzbaren Code ist die
korrekte Codierung der Daten sowie die Einhaltung einer
definierten Bedruckungsqualität. Beides ist über qualitätssichernde Maßnahmen zu gewährleisten.
Bei der Qualitätsprüfung eines Codes ist grundsätzlich
zwischen der Lesekontrolle und der Druckqualität zu unterscheiden. Die Lesekontrolle prüft den Codeinhalt und
stellt somit die Interpretation des Dateninhalts und die
Richtigkeit der Daten sicher. Hierzu sind die Festlegungen der vorherigen Kapitel sowie folgendes zu beachten:
Beim Digitaldruck ist jeder Druck als individuell zu
betrachten. Daher muss der Codeinhalt jeder Packung mittels Lesekontrolle überprüft werden.
Bestimmung der Bedruckungsqualität:
Die Druckqualität ist die physikalische Güte der Bedruckung. Die Festlegung und Einhaltung einer definierten
Mindestdruckqualität sichert eine hohe Erstleserate.
Dazu dienen die Ausführungen in diesem Kapitel. Weitere
Details befinden sich in Anhang D.
Gemäß der delegierten Verordnung ist die Druckqualität nach bestimmten Parametern (siehe Anhang D.5) zu
beurteilen.
Dabei hat der pU die Mindestdruckqualität für die Lesbarkeit des Codes entlang der gesamten Lieferkette und
während des Nutzungszyklus1
 zu ermitteln und dabei für
die in Anhang D.5 genannten Parameter die Grenzwerte
festzulegen.
Praktikabler durchführbar ist die in Art. 6 Abs. 4 der delegierten Verordnung gegebene Möglichkeit, dass bei
einer Druckqualität von mindestens 1,5 gemäß der Norm
ISO/IEC 15415 (siehe nebenstehende Tabelle) die Anforderungen als erfüllt gelten, sofern der pU auch die Alterungs- und Abnutzungseffekte der Bedruckung mit in
Betracht gezogen hat.
1 Minimaler Zeitraum gemäß der delegierten Verordnung: Ein
Jahr über das Verfalldatum hinaus oder fünf Jahre ab dem Inverkehrbringen des Arzneimittels. Maßgebend ist jeweils der
längere Zeitraum.
Seite 18 All contents copyright © securPharm e.V. | Deutsch V 2.03
Qualitätsstufen nach ISO/IEC 15415
ISO/
IECKlasse
ANSIGrad
Ø bei Mehrfachmessung* Bedeutung
4 A 3,5–4,0 Sehr Gut
3 B 2,5–3,49 Gut
2 C 1,5–2,49 Befriedigend
1 D 0,5–1,49 Ausreichend
0 F < 0,5 Durchgefallen
* Die Mehrfachmessung ist in der aktuellen Fassung der ISO/
IEC 15415 (Dez. 2011) entfallen. Implizit entspricht daher die
Mindestanforderung 1,5 immer der ISO/IEC Klasse 2.
Handelsübliche Scanner sind in der Lage, Codes auch
dann noch zu lesen, wenn die ISO/IEC Klasse 1,5 (ISO/
IEC 15415) unterschritten wird. Die technischen Variationen der handelsüblichen Scanner sind allerdings sehr
groß.
Den Anwendern wird auferlegt, die Scanner so auszuwählen bzw. zu parametrieren, dass Codes der ISO/IEC
Klasse 0,5 (ISO/IEC 15415) noch lesbar sind.
Basierend auf dieser Festlegung erfüllt eine Bedruckung
in einer geringeren Qualität als 1,5 die Anforderung der
delegierten Verordnung. Bei dieser Festlegung hat der
pU ebenfalls die Alterungs- und Abnutzungseffekte der
Bedruckung mit in Betracht zu ziehen.
Um allerdings eine sehr hohe Erstleserate zu erreichen,
darf der pU die Anforderung von 1,5 (nach ISO/IEC
15415) nicht permanent unterschreiten.
Zur Qualitätsprüfung wird in der Praxis häufig eine 100%
Lesekontrolle (mit oder ohne Inline Pseudo Grading) mittels Inline-Systemen in Kombination mit einer messtechnischen Stichprobenkontrolle durchgeführt.
Hinweis zu Stichproben2
:
Die Qualitätssicherung beim Arzneimittel-Hersteller arbeitet üblicherweise mit Stichprobenplänen. Die Stichprobenpläne legen fest, wie viele Stichproben den Test
bestehen müssen und lassen üblicherweise auch eine
bestimmte Menge an Proben zu, die die Mindestqualität
unterschreiten3
. Der pU ist für die Definition der Stichprobenpläne verantwortlich.
Hinweis zu den Messgeräten:
Messgeräte (siehe Anhang D.3), die gemäß ISO/IEC
15415 arbeiten, sind vom Anwender auf die entsprechende Applikation hin zu konfigurieren. Je nach Hersteller
variiert die Anzahl der Parameter.
Die vorliegenden Codierregeln sind die Anwenderspezifikation gemäß ISO/IEC 154154
 und somit die Vorgabe für
die korrekte Konfiguration eines Messgerätes zur Druckqualitätskontrolle eines Data Matrix Codes.
Um vergleichbare und valide Messergebnisse zu
erhalten, gilt:
Die Mindestqualität ist bei einer Beleuchtung mit Rotlicht
(660 nm), einer Messblende von 80% der Modulbreite
des Codes sowie mit einer vierseitigen Beleuchtung unter
45° zu ermitteln. Weitere Details sind in Anhang D.4 zu
finden.
2 Die Norm ISO/IEC 15415, die in der delegierten Verordnung
Art. 6, Abs. 4 angeführt wird bezieht die Stichprobensystematik
im Kapitel 5.1, „Allgemeines“ mit ein: “Information on sampling
plans may be found in the following: ISO 3951-1, ISO 3951-2,
ISO 3951-3, ISO 3951-5 or ISO 2859-10”. Die Stichprobensystematik wird somit implizit Bestandteil der delegierten Verordnung
Art. 6, Abs. 4, da Kapitel 5.1 der normative und damit verbindliche Teil der Norm ISO/IEC 15415 ist.
3 Ein Code in geringerer Qualität könnte im Extremfall zur
Nichtlesung führen.
4 Die ISO/IEC 15415 legt die Regeln zur Qualitätsbestimmung
fest. Die Norm verlangt, die Lichtart, Beleuchtungsanordnung
und Messblende in der Anwenderspezifikation festzulegen.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 19
8 Interoperabilität auf Basis von
XML-Standards
Im Anhang A und C ist ein vorzugsweise anzuwendender
Standard beschrieben, der auf allgemeinen XML-Standards beruht und die Datenbezeichner neutral beschreibt. Dies ermöglicht den offenen Datenaustausch
wie in Abbildung 8 beschrieben, unabhängig von Symbolik und Datenstrukturen.
Die in Anhang A definierten XML-Knoten dienen dem
standardisierten XML-Datenaustausch.
Abbildung 8: Datenaustausch zwischen Lesegrät und
System auf XML-Basis
Seite 20 All contents copyright © securPharm e.V. | Deutsch V 2.03
Anhang A
Übersicht und Referenz der Datenbezeichner
Die folgende Tabelle spezifiziert die Ausprägung der einzelnen Datenbezeichner:
Datenelemente
XMLKnoten DI AI Datentyp
Datenformat
Zeichenlänge Zeichenvorrat
Pharmacy
Product
Number (PPN)
<PPN> 9N AN — 4–22 0–9; A–Z
keine Sonderzeichen, keine Kleinschreibung, keine Umlaute
National Trade
Item Number
(NTIN)
<GTIN> 8P 01 N — 14 0–9
Seriennummer <SN> S 21 AN — 1–20 numerische oder
alphanumerische Zeichen,
keine Umlaute
Chargenbezeichnung
<LOT> 1T 10 AN — 1–20 numerische oder
alphanumerische Zeichen,
keine Umlaute
Verfalldatum <EXP> D 17 Datum YYMMDD 6 0–9
Hinweis:
Details zu den Datenelementen finden sich in Kapitel 4 und Kapitel 5. Dort sind u. a. die zur Anwendung kommenden
Zeichenlängen und sind die Besonderheiten des Formats beim Verfalldatum beschrieben.
Empfehlungen an die pUs zum Zeichenvorrat für Seriennummer und Chargenbezeichnung:
a) Die Zeichenkette sollte entweder nur Großbuchstaben oder nur Kleinbuchstaben des lateinischen Alphabets
enthalten.
b) Zur Vermeidung von menschlichen Lesefehlern sollte der pU in Abhängigkeit des von ihm angewandten Schriftfonts und der Qualität seines Druckbildes verwechslungsgefährdete ähnliche Zeichen ausschließen. Hierunter
fallen z. B.: i, j, l, o, q, u sowie I, J, L, O, Q, U.
c) Einige Sonderzeichen werden zwar technisch verarbeitet1
, sollten jedoch nicht verwendet werden, da bei diesen
das Risiko einer Fehlinterpretation sehr hoch ist. Ein falsch interpretierter Code führt dazu, dass eine Packung
nicht verifiziert werden kann und damit nicht abgabefähig ist.
Sollten Trennzeichen innerhalb einer Chargenbezeichnung notwendig sein, so wird empfohlen den Bindestrich „-“
oder den Unterstrich „_“ oder den Punkt „.“2
 zu verwenden.
1 Von der technischen Verarbeitung ausgeschlossen sind die Sonderzeichen mit den dezimalen ASCII-Codewerten 35 (#), 36 ($), 64
(@), 91 ([), 92 (\), 93 (]), 94 (^), 96 (`), 123 ({), 124(|), 125 (}), 126 (~) und 127 (¦) sowie alle Steuerzeichen (ASCII-Codewert 00-31).
Prinzipiell sind alle ASCII-Zeichen mit einem dezimalen Wert > 127 ausgeschlossen. Der technisch zulässige Zeichenumfang entspricht
dem „GS1 AI encodable character set 82“ (GS1 General Specifications, section 7.11 (Abbildung 7/11-1)).
2 Die Verwendung des Punkts wird besonders empfohlen, da dieser bei deutschen und englischen Tastaturen identisch belegt ist.
Bei falscher Sprachwahl der eingesetzten Tastaturscanner ist somit die Gefahr der Fehlinterpretation per se nicht gegeben.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 21
Anhang B
Emblem zum Code
Als Emblem zum Code ist die Zeichenfolge „PPN“ in der Schriftart „OCR-B“ festgelegt. Die graphische Ausprägung ist
nachstehender Skizze zu entnehmen:
c d
f e
a
b
Nominale Maße:
a: ergibt sich aus gewählter Modul- und Matrixgröße
b: ist bei quadratischen Codes gleich a, bei rechteckigen Codes entsprechend der Modul- und Matrixgröße
c: 0,4 * a
d: *)
e: ergibt sich aus der geforderten Ruhezone*)
(Ruhezone siehe Kapitel 6.3)
f: ergibt sich aus der Schrifttype und Maß c
*) Die Maße d und e sind so zu wählen, dass das Emblem dem
Code zugeordnet ist.
Toleranzen: Die Toleranzen können entsprechend dem gewählten Druckverfahren frei festgelegt werden.
Folgende Ausrichtungen sind prinzipiell möglich:
In Ausnahmefällen kann das Emblem auch auf einer anderen, angrenzenden Fläche aufgebracht werden.
Seite 22 All contents copyright © securPharm e.V. | Deutsch V 2.03
Anhang C
Interoperabilität auf der Basis von XML-Beschreibungen (informativ)
C.1 Allgemeines
Für die Hersteller, den Großhandel, die Apotheken und
die Kliniken ist die Interoperabilität der Codierungen eine
Voraussetzung für das Lesen und die eindeutige Identifikation der Datenelemente. Bei einer durchgängigen Interoperabilität ist es den Beteiligten möglich, ihre Prozesse
kostengünstig zu betreiben. Die gemeinsame Basis dafür
sind die Standards IEC 15434 Syntax for High Capacity
Media, ISO/IEC 15459 Unique Identification sowie die
System- und Datenbezeichner nach ISO/IEC 15418.
Um Herstellern und Nutzern im pharmazeutischen
Bereich eine noch höhere Interoperabilität zu bieten, wird in diesem Anhang ein Standard zur Interpretation der Daten, basierend auf XML beschrieben. Dies gilt sowohl für die Datenübertragung zum
Drucker als auch für die Datenübertragung vom
Codeleser an die angeschlossenen Systeme.
Der in diesem Anhang beschriebene XML-Standard bezieht sich ausschließlich auf die Dateninhalte und damit
nicht auf die Layouteigenschaften des Codes, zu denen
die Festlegungen der Klarschriftbedruckung und die der
Symbologie (z.B. Data Matrix Code) gehören. Bei der
Datenübertragung werden nach dem hier beschriebenen Standard die Daten unabhängig von den im Code
verwendeten Datenbezeichnern einheitlich mit neutralen
XML-Knoten bezeichnet. Es bilden sich folgende Ebenen
in der Darstellung der Daten aus:
Applikation: XML-Knoten
Datenhülle: ISO/IEC 15434 z. B. Format 05, Format
06 etc.
Datenstruktur: Data Identifier (DI) oder Application
Identifier (AI)
Symbologie: z.B. Data Matrix Code
C.2 Data-Format-Identifier (DFI)
Bei der Übertragung der Datenelemente im XML-Standard werden die Eigenschaften zur Darstellung der Daten
im Code dem Data-Format-Identifier (DFI) zugeordnet
und lediglich dieser übertragen.
Der DFI sagt aus, welche Datenhülle nach ISO/IEC 15434,
welche Datenbezeichner (AI oder DI) und ob ein Makro
nach ISO/IEC 16022 zu verwenden ist. Die Zuweisungen
des DFI können aus Tabelle 1 entnommen werden.
XML
Data
Format
Identifier
(DFI)
FormatID
nach ISO/
IEC 15434
Data-TypIdentifier
nach ISO/
IEC 16022
Data Identifier/Application
Identifier
nach ISO/
IEC 15418
IFA 06 Macro 06 DI-ASC
GS1 FNC1 AI-GS1
Tabelle 1: Data-Format-Identifier (DFI)
Der DFI kann die Werte „IFA“ oder „GS1“ annehmen und
wird im dem gleichlautenden Attribut des übergeordneten XML-Knoten <Content> übertragen.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 23
C.3 XML-Knoten für Daten
In unten stehender Tabelle sind die XML-Knoten für die
Daten und deren Zuordnung zu den Datenbezeichnern
aufgeführt:
Datenbezeichner
XMLKnoten
DI
dfi=“IFA“
AI
dfi=“GS1“
Beschreibung
<PPN> 9N Produktcode
<GTIN> 8P 01 Produktcode
<LOT> 1T 10 Chargenbezeichnung
<EXP> D 17 Verfalldatum
<SN> S 21 Seriennummer
Tabelle 2: XML-Knoten für Daten
Die vollständige Auflistung der derzeit definierten Knoten
ist im Anhang A aufgeführt. Auf dieser technischen Ebene der Beschreibung gibt es zwischen NTIN und GTIN
keine Unterscheidung. Deshalb wird der umfassende
Begriff GTIN verwendet.
Der XML-Knoten <Content> umhüllt die „Datenknoten“ (siehe C.4 und C.5).
Aus den XML-Daten und dem darin enthaltenen Wert des
„DFI“ leiten die Drucker alle notwendigen Informationen
zur Erzeugung des Data Matrix Codes ab. Das beinhaltet die Datenelemente, die Data Identifier respektive die
Application Identifier, die Trennzeichen und den Header.
C.4 Anwendung
Sowohl bei der Datenübergabe an die Druckertreiber, als
auch bei der Datenausgabe von den Codelesern kann
die XML-Beschreibung angewendet werden (siehe schematische Darstellung):
Driver
MESSystem
Terminal
Printer
Terminal
Reader
MESSystem
AnwenderApplikationsebene Systemebene
XML-Tag
Datenbezeichner
Code
Printer Reader
Abbildung 9: Datenaustausch auf XML-Basis
Die Treiber zur Interpretation der XML-Beschreibung
können Bestandteil der übergeordneten Systeme (MES)
oder der Drucker (Printer) und Codeleser (Reader) sein.
Die Verwendung der einheitlichen Beschreibung steigert
die Interoperabilität und hilft Fehler zu vermeiden. Auch
die Unsicherheit hinsichtlich nichtdruckbarer Steuerzeichen in Übertragung und Interpretation ist bei der XMLBeschreibung eliminiert. Beim Lesen der Codes setzen
die Codeleser den Dateninhalt in die XML-Struktur und
die entsprechenden Knoten um.
Bei der Datenübertragung vom Codeleser an die übergeordneten Systeme werden standardmäßig lediglich die
Daten ohne den „DFI“ übertragen. Optional kann dieser
zusätzlich mit ausgegeben werden und ist dann von Interesse, wenn im Code z.B. die korrekte Verwendung der
Strukturen zu verifizieren ist.
Allgemeine XML-Beschreibung bei der Datenübertragung zum Drucker und vom Codeleser:
<Content dfi=“value_dfi“>
<Daten _ 1>value _ Daten _ 1</Daten _ 1>
<Daten _ 2>value _ Daten _ 2</Daten _ 2>.
<Daten _ n>value _ Daten _ n</Daten _ n>
</Content>
Bei der Übertragung vom Codeleser ist der Wert „dfi“
optional.
Seite 24 All contents copyright © securPharm e.V. | Deutsch V 2.03
C.5 Beispiele
An folgenden Beispielen soll unter Verwendung der vier Datenelemente Produktcode, Chargenbezeichnung, Verfalldatum und Seriennummer die Anwendung gezeigt werden:
Beispiel 1: Datenübertragung an Drucker – ASC-Format
Produktcode: PPN Datenbezeichner: DI Data Format Identifier: IFA
System
PPN: 111234567842
Batch: 1A234B5
Verfalldatum: 31.12.2015
Serien-Nr.: 1234567890123456
Codierung: „IFA“
<Content dfi=“IFA“>
<PPN>111234567842</PPN>
<LOT>1A234B5</LOT>
<EXP>151231</EXP>
<SN>1234567890123456</SN>
</Content>
Data Carrier
Mac069N111234567842Gs
1T1A234B5Gs
D151231Gs
S1234567890123456
Drucker
Beispiel 2: Datenübertragung an Drucker – GS1-Format
Produktcode: GTIN1 Datenbezeichner: AI Data Format Identifier: GS1
System
GTIN: 04150123456782
Batch: 1A234B5
Verfalldatum: 31.12.2015
Serien-Nr.: 1234567890123456
Codierung: „GS1“
<Content dfi=“GS1“>
<GTIN>04150123456782</GTIN>
<LOT>1A234B5</LOT>
<EXP>151231</EXP>
<SN>1234567890123456</SN>
</Content>
Data Carrier
FNC104150123456782
101A234B5FNC1
17151231
211234567890123456
Drucker
Beispiel 3: Datenübertragung vom Codeleser – ASC-Format
Produktcode: PPN Datenbezeichner: DI Data Format Identifier: IFA
Codeleser
<Content dfi=“IFA“>
<PPN>111234567842</PPN>
<LOT>1A234B5</LOT>
<EXP>151231</EXP>
<SN>1234567890123456</SN>
</Content>
System
PPN: 111234567842
Batch: 1A234B5
Verfalldatum: 31.12.2015
Serien-Nr.: 1234567890123456
Codierung: „IFA“
Data Carrier
Mac069N111234567842Gs
1T1A234B5Gs
D151231Gs
S1234567890123456
Beispiel 4: Datenübertragung vom Codeleser – GS1-Format
Produktcode: GTIN1 Datenbezeichner: AI Data Format Identifier: GS1
Codeleser
<Content dfi=“GS1“>
<GTIN>04150123456782</GTIN>
<LOT>1A234B5</LOT>
<EXP>151231</EXP>
<SN>1234567890123456</SN>
</Content>
System
GTIN: 04150123456782
Batch: 1A234B5
Verfalldatum: 31.12.2015
Serien-Nr.: 1234567890123456
Codierung: „GS1“
Data Carrier
FNC104150123456782
101A234B5FNC1
17151231
211234567890123456
Rückfragen und Anregungen zu den in diesem Anhang beschriebenen Festlegungen sind willkommen und an
securPharm zu richten.
1 Auf dieser technischen Ebene der Beschreibung gibt es zwischen NTIN und GTIN keine Unterscheidung. Deshalb wird der umfassende Begriff GTIN verwendet.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 25
Anhang D
Details zur Qualitätsprüfung des Data Matrix Codes
D.1 Allgemeines
Die Qualitätsprüfung setzt sich aus den Komponenten
Lesekontrolle (D.2) und Messung der Druckqualität (D.3)
zusammen. Ob die Lesekontrolle nach D.2.1 oder nach
D.2.2 durchgeführt wird, legt der pU in Abhängigkeit von
seinen Prozessen fest.
Es muss durch die Lesekontrolle sichergestellt werden, dass ein Code mit dem korrekten Inhalt auf jeder
Packung ist. Packungen ohne Code oder mit falschem
Inhalt werden ausgeschleust. Nach dieser Prüfung ist
die Seriennummer valide und kann, zusammen mit den
anderen notwendigen Daten, in das ACS-PU-System
übernommen werden.
Lesesysteme variieren in der Ausführung sehr stark. Manuelle Scanner sind üblicherweise sehr fehlertolerant,
während Inline-Hochgeschwindigkeitsscanner höhere
Ansprüche an die Druckqualität stellen. Identische Druckqualitäten können deshalb bei verschiedenen Lesesystemen zu unterschiedlichen Erstleseraten führen.
D.2 Lesekontrolle
Die Lesekontrolle ermittelt, ob
• der Code vorhanden ist,
• die korrekte Symbologie verwendet wurde und
• der Inhalt mit den Vorgaben übereinstimmt.
Die Überprüfung der Klartextaufdrucke mit dem Codeinhalt ist ebenfalls Bestandteil einer Lesekontrolle, da diese Klartextinformationen zu den geforderten Bestandteilen des individuellen Erkennungsmerkmals zählen. Beim
Digitaldruck ist jede einzelne Packung zu kontrollieren
(100% Lesekontrolle).
Im Verpackungsprozess ist sicherzustellen, dass nicht
vorhandene, nicht lesbare oder von den Vorgaben abweichende Codes ausgeschleust werden.
Die Lesekontrolle beinhaltet keine Messung der Druckqualität: Zu deren Beurteilung ist eine Messung dergestalt, wie sie in Art. 6 der delegierten Verordnung gefordert wird, obligatorisch.
Üblicherweise wird die Druckqualität mit einem Stichprobenmessgerät ermittelt (siehe D.3).
D.2.1 Manuelle Lesekontrollen
Bei Arzneimitteln, die in Kleinmengen produziert werden,
kann die Lesekontrolle mittels eines manuell bedienten
Scanners durchgeführt und die Daten in die Datenbank
übergeben werden. Die Klartextdaten können in diesem
Fall entweder rein manuell oder mit der Unterstützung
des manuellen Scanners überprüft werden.
D.2.2 Inline-Kontrolle
Bei den Inline-Kontrollen handelt es sich um eingebaute,
vollautomatische Erfassungssysteme, die die Aufgaben
einer im vorhergehenden Kapitel D.2 beschriebenen Lesekontrolle übernehmen. Die Inline-Lesekontrollsysteme
sind für Logistikprozesse auf eine hohe Leserate und
Fehlertoleranz durch entsprechende Softwarealgorithmen und optoelektronische sowie mechanische Eigenschaften optimiert.
Die Inline-Kontrolle kann eine reine Lesekontrolle sein
oder zusätzlich ein Pseudo Grading ausführen. Pseudo
Grading ist die erweiterte Fähigkeit der Lesesysteme zur
Analyse und Bestimmung der Druckqualität in Anlehnung
an ISO/IEC 15415.
Zu beachten ist jedoch, dass die Bewertung der Kontraste
und Druckgenauigkeiten in Anlehnung an ISO/IEC 15415
keine Messung ist. Gleichwohl können diese Ergebnisse zur Beurteilung qualitativer Parameter und vor allem
zur Erkennung von Schwankungen in der Druckqualität
herangezogen werden. Dies bietet den Vorteil, dass die
Lesekontrolle aller Packungen mit einem Pseudo Grading
zur Beurteilung der Druckqualität verbunden ist.
Eine messtechnische Beurteilung gemäß ISO/IEC 15415
(D.3) durch die Inline-Kontrollen scheitert derzeit an den
Gegebenheiten der zur Verfügung stehenden Systeme.
Die Einstellungen zur effizienten Codelesung bezüglich
Belichtung, Schärfe, Geometrie sowie vorhandenes, unterschiedliches Umgebungslicht und die Nachjustierung
der Positionen von Kamera und Beleuchtung führen zu
Ergebnissen in der Beurteilung der Druckqualität, die von
einer echten Messung (D.3) mehr oder weniger stark ab-
Seite 26 All contents copyright © securPharm e.V. | Deutsch V 2.03
weichen. Diese teilweise unsystematischen Abweichungen lassen sich nicht justieren und können zu scheinbar
zufälligen unterschiedlichen Ergebnissen führen.
Um dem Rechnung zu tragen, werden parallel zur Inline-Kontrolle typischerweise zusätzliche Stichprobenmessungen durchgeführt (siehe D.3). Der Stichprobenumfang und die -frequenz hängen von der Stabilität der
Bedruckungsverfahren und des Pseudo Gradings ab.
Sofern ein Gerät zur Inline-Kontrolle die messtechnischen
Anforderungen bezüglich Kalibrierung und Justierung
sowie die Rückführbarkeit der Ergebnisse auf nationale
Standards nicht erfüllen kann, ist eine Stichprobenmessung zwingend notwendig. Nur dann sind die Vorgaben
aus der delegierten Verordnung erfüllt.
D.3 Messung gemäß ISO/IEC 15415
Die delegierte Verordnung fordert in Art. 6 die Beurteilung
der Druckqualität.
Dazu werden üblicherweise Messgeräte benutzt, deren
Konstruktion durch die Norm ISO/IEC 15415 vorgegeben ist. Es handelt sich dabei um optische Messgeräte,
die eine definierte Messgenauigkeit aufweisen (ISO/IEC
15426-2) und deren Ergebnisse auf nationale Standards
rückführbar sind (z.B. PTB, NIST).
Neben den in Kapitel 7 erwähnten Hinweisen zu den Parametern der Messgeräte ist deren Justierung und Kalibration (DIN 1319-1) zwingend zu beachten.
D.4 Messbedingungen nach ISO/IEC
15415
Der zu messende Code ist in Kapitel 6.1, die Druckqualitätskontrolle ist in Kapitel 7 beschrieben worden.
Die Prüfparameter (siehe D.5) sind nur dann aussagefähig und vergleichbar, wenn diese unter definierten Bedingungen bestimmt werden. Die Norm ISO/IEC 15415
zeigt verschiedene Möglichkeiten auf und fordert von der
Anwenderspezifikation diese Bedingungen festzulegen.
Die Vorgaben dazu lauten wie folgt:
Eigenschaft Festlegung
Lichtart Rotlicht, Wellenlänge 660 nm
(+/-10 nm)
Filterung
(synthetische
Apertur)
80% der Matrixzellengröße (Modulgröße) des jeweilig zu messenden
Codes
Beleuchtungswinkel
4 Beleuchtungen, die unter 45° das
Sichtfeld von vier Seiten ausleuchten
Kamerawinkel
*)
90° über dem Code (senkrecht zur
Ebene der Verpackung)
Abstand *) So, dass die Beleuchtungswinkel
erfüllt werden, das Bild im Fokus ist
und die Auflösung ausreichend ist.
Auflösung *) Mindestens 10 x 10 Kamerapixel
pro Matrixzelle oder weniger, wenn
nachweisbar ist, dass die Messgenauigkeitsforderung der ISO/IEC
15426-2 eingehalten wird. Weniger
als 5 x 5 Kamerapixel führen nach
bisheriger Erfahrung zu unbrauchbaren Ergebnissen.
*) in der Regel durch die Konstruktion des Messgerätes vorgegeben.
D.5 Parameter zur Druckqualität
Die delegierte Verordnung gibt die mindestens notwendigen Parameter zur Bestimmung der Druckqualität vor.
Zum besseren Überblick sind in folgender Tabelle die
Begriffe aus der delegierten Verordnung und den
entsprechenden Normen jeweils in deutscher und
englischer Sprache zugeordnet sowie deren technische
Bedeutung jeweils erläutert.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 27
Tabelle 3: Prüfparameter zur Bestimmung der Druckqualität:
Art. 6 Abs. 1
der Delegierten Verordnung Norm ISO/IEC 15415 Technische Bedeutung
englische
Fassung
deutsche
Fassung Englisch deutsch1
(a) the contrast
between the light
and dark parts
(a) Kontrast
zwischen hellen
und dunklen
Elementen
SC = Symbol
Contrast
Symbolkontrast
Der Kontrast wird zwischen der hellsten und dunkelsten Stelle im
gesamten Symbol bestimmt. Dazu wird jeweils die hellste und dunkelste Matrixzelle (einschließlich der festen Muster) bestimmt. Die
Differenz dieser Reflexionswerte ist der Symbolkontrast. Abnehmende Werte führen zur Abwertung dieses Parameters.
(b) the uniformity
of the reflectance
of the light and
dark parts
(b) Homogenität
der Reflexion
heller und dunkler
Elemente
Modulation,
Reflectance
Margin and
Contrast
uniformity
Modulation,
Reflexionsbereich und
Kontrastgleichmäßigkeit
Idealerweise sollen alle weißen Bereiche die gleichen Reflexionswerte aufweisen, wie auch die schwarzen untereinander. Durch
Materialtransparenz, Druckzuwächse, Gitterverzerrungen und ungleichmäßige Schwärzungen des Drucks wie auch ungleichmäßige
Helligkeiten des Substrates wird die Ungleichmäßigkeit der Reflexionswerte größer. Dies führt zur Abwertung dieses Parameters.
(c) the axial nonuniformity
(c) axiale Inhomogenität
AN = Axial
Nonuniformity
Axiale
Ungleichmäßigkeit
Die axiale Verzerrung bewertet, ob ein Symbol in der Gesamtheit gestaucht oder gestreckt gedruckt wurde. Je größer die Verzerrungen
werden, umso schlechter wird dieser Parameter bewertet.
(d) the grid nonuniformity
(d) Inhomogenität
des Rasters
GN = Grid
Nonuniformity
Gitterungleichmäßigkeit
Die Gitterungleichmäßigkeit betrachtet die Matrix des Codes
im Detail. Abweichungen einzelner Matrixzellen von der idealen
Schachbrettgeometrie führen zur Abwertung dieses Parameters.
(e) the unused
error correction
(e) nicht genutzte
Fehlerkorrektur
UEC =
Unused Error
Correction
Ungenutzte
Fehlerkorrektur
Einzelne weiße oder schwarze Matrixzellen, die durch Fehlstellen
oder Flecken die falsche Farbe haben, werden durch die Fehlerkorrektur erkannt und die Daten aus den redundanten Matrixzellen
rekonstruiert. UEC wird entsprechend der genutzten Fehlerkorrektur
abgewertet.
(f) the fixed
pattern damage
(f) Beschädigung des festen
Musters
FPD = Fixed
Pattern
Damage
Beschädigung
der festen
Muster
Der Data Matrix Code enthält Bereiche, die zur Lagebestimmung
und zur Gitterrekonstruktionen dienen. Diese Bereiche beinhalten
keine Daten. Die Beschädigung dieser Muster führt zur Abwertung
dieses Parameters.
(g) the capacity
of the reference
decode algorithm
to decode the
Data Matrix.
(g) Kapazität des
Referenzdekodierungsalgorithmus
zur Dekodierung
der Datenmatrix
Decode Dekodierung Die Dekodierung und Gitterrekonstruktion erfolgt bei einer Codemessung mit dem normierten Referenzdekodieralgorithmus. Wenn
die Dekodierung damit scheitert, führt dies zur Abwertung dieses
Parameters.
— — Contrast
Uniformity
Kontrastgleichmäßigkeit
Es werden MOD2
 Werte für alle Codewörter bestimmt. Die MOD
Werte werden für die Bestimmung der Modulation und des
Reflexionsbereiches verwendet. Die Kontrastgleichmäßigkeit ist
der schlechteste einzelne MOD Wert (informativ, relevant für die
Kalibrierung nach ISO/IEC 15426-2).
— — Print Gain Druckzuwachs Informativer Parameter der angibt, ob ein Symbol überdruckt (zu
fett) oder unterdruckt (zu dünn) ist.
— — Module Size Modulgröße Die Größe einer Matrixzelle des Gesamtcodes wird als Modulgröße
bezeichnet. Von der Modulgröße hängen die Lesegeräteeigenschaften bezüglich der Scannertiefenschärfe, der Scannerauflösung und
des Mindestleseabstandes ab.
— — Matrix Size Matrixgröße Der gesamte Code baut sich aus einzelnen Matrixzellen (= Module)
einer bestimmten, identischen Modulgröße auf. Die Norm ISO/ IEC
16022 definiert als kleinste Matrixgröße 10x10 Module und als maximale Matrixgröße 144x144. In praktischen Anwendungen wird der
Bereich der erlaubten Matrixgrößen eingeschränkt, um das Verhältnis der Kameraauflösung zur Größe der Matrix zu begrenzen und
um eine ausreichend große Anzahl von Kamerapixeln pro Modul zur
Verfügung zu haben. Dies ist für die Lesesicherheit erforderlich.
Die Endbewertung wird von dem Prüfparameter bestimmt, der das schlechteste Messergebnis aufweist. Die
Qualitätsstufen sind in Kapitel 7 tabellarisch dargestellt.
1 Die deutschen Bezeichnungen wurden von den Autoren vorgenommen, da keine deutsche Fassung der Norm existiert.
2 MOD ist die Bewertung der Modulation für ein einzelnes
Codewort des Data Matrix Codes. Ein Codewort ist ein kleiner
Teilausschnitt des Codes, der immer aus acht Matrixzellen besteht.
Seite 28 All contents copyright © securPharm e.V. | Deutsch V 2.03
Anhang E
Glossar
Grundsätzlich gelten die Begriffe und Definitionen
der ISO/IEC 19762.
Im Folgenden aufgeführt sind die in diesem Dokument
verwendeten Begriffe und Abkürzungen:
ACS PharmaProtect GmbH (ACS): Die Betreibergesellschaft des Datenbanksystems der pharmazeutischen
Industrie (www.pharmaprotect.de) bei securPharm.
AMG: Zweck des Arzneimittelgesetzes (AMG) ist es, im
Interesse einer ordnungsgemäßen Arzneimittelversorgung von Mensch und Tier für die Sicherheit im Verkehr
mit Arzneimitteln, insbesondere für die Qualität, Wirksamkeit und Unbedenklichkeit der Arzneimittel nach Maßgabe der im AMG enthaltenen Vorschriften zu sorgen (siehe
§ 1 AMG).
Application Identifier (AI): Durch die Anwender von
GS1 entwickelte Datenbezeichner, die genau definieren,
welche Dateninhalte wie verschlüsselt werden. Diese
sind weltweit gültig und multisektoral einsetzbar nach
ISO/IEC 15418. Im deutschen Sprachraum von GS1 unter
dem Begriff „Datenbezeichner“ publiziert.
Artikelnummer: Ist die Nummer, die einen Artikel oder
ein Produkt eindeutig identifiziert. Ein Synonym zur Artikelnummer ist die Produktnummer. In diesem Dokument wird der Begriff Artikelnummer verwendet, wenn
die Identifizierung des Artikels im Handel gemeint ist. Im
Gegensatz zum Produktcode, der Bestandteil des UI im
Sinne der delegierten Verordnung ist. Somit kann einem
Artikel eine Artikelnummer und ein Produktcode zugeordnet sein.
ASC-Format: Damit ist eine Struktur gemeint, die gemäß
ISO/IEC 15434 das Format 6 und die ASC MH10 Data
Identifier (DI) gemäß ISO/IEC 15418 (Referenz auf ANSI
MH10.8.2) nutzt. Auf diesem Format basieren die Spezifikationen des IFA Coding Systems. Siehe auch unter
„Data Identifier“.
Bar Code: Optischer Datenträger aus Strichen bestehend (auch Strichcode genannt). Umgangssprachlich
werden 2-dimensionale Matrixcodes u.a. als 2D Barcodes bezeichnet. Dazu zählt auch der Data Matrix Code.
Blue Box: Bei in Europa in einem europäischen Verfahren zugelassenen Arzneimitteln sind die Packungsinformation nach den europäischen Vorgaben des Artikels
57 der Richtlinie 2001/83/EG zu erstellen. Die landesspezifischen Anforderungen sind in der sog. „blue box“
aufzunehmen (visuell erkennbar durch eine blaue Umrahmung). Welche das sind, gibt die Europäische Zulassungsbehörde (EMA) bzw. die Koordinierungsgruppe
für Humanarzneimittel (CMDh) in den „blue-box-requirements“ vor:
EMA:
• Notice to Applicants
• http://ec.europa.eu/health/documents/eudralex/vol2/index_en.htm
• Volume 2C Regulatory, „Guideline on the packaging
information of medicinal products for human use authorised by the Union“; ANNEX: ‚Blue box‘.
CMDh:
• http://www.hma.eu
• Procedural Guidance
• Application for Marketing Authorisation ( MA ), „Bluebox requirements“.
Code 39: Ein Barcode bzw. Strichcodetyp, der in der
ISO/IEC 16388 spezifiziert ist. Der Platzbedarf dieses
Codes ist, bei vergleichsweise geringen Datenmengen,
groß. Bis auf weiteres wird der Code 39 als Datenträger
für die Pharmazentralnummer (PZN) benutzt.
Continuous Ink-Jet (CIJ): Damit wird ein Tintenstrahldruckverfahren bezeichnet. Typischerweise erzeugt
dieses Druckverfahren Dotcodes, die hier im Glossar erwähnt werden. Das Druckverfahren erzeugt einen ständig
laufenden Strahl aus Tintentropfen, der elektrostatisch
abgelenkt wird. Dabei verdunstet Lösemittel. Aufgrund
des hohen Lösemittelanteiles trocknet und haftet die Tinte sehr gut auf allen nicht saugenden Oberflächen. Die
Auflösung ist niedrig.
Data Matrix Code: Zweidimensionaler Matrixcode,
der aus quadratischen Elementen besteht. In der Ausführung ECC200 nach ISO/IEC 16022 beinhaltet der
Code eine Fehlerkorrektur gemäß dem Reed Solomon
Verfahren für fehlende Punkte oder beschädigte Stellen.
Die gleichfarbigen, benachbarten Elemente des Codes
sollen ohne Unterbrechung direkt ineinander übergehen.
(In der deutschen Fassung der delegierten Verordnung
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 29
(EU) 2016/161 wird der Data Matrix Code mit Datenmatrix
übersetzt).
Data Identifier (DI): Von dem „ASC MH10 Data Identifier
Maintenance Committee“ vergebene Datenbezeichner,
die in dem internationalen Standard ANSI MH10.8.2 gelistet sind. Der Datenbezeichner schließt immer mit einem
Alphazeichen ab, diesem kann, zur Unterscheidung von
Varianten, eine ein-, zwei- oder dreistellige Zahl vorangestellt sein.
Datenbezeichner: Zur Kenntlichmachung eines Dateninhalts werden diesem genormte Identifikatoren vorangestellt. Die am häufigsten eingesetzten Identifikatoren
sind die ASC MH10 Data Identifier (DI) und die GS1 Application Identifier (AI). In der ANSI MH10.8.2 sind beide
Typen sowohl getrennt aufgeführt als auch wechselseitig
gemappt. Zur sprachlichen Vereinfachung wird in
diesem Dokument, sofern von dem DI und AI die
Rede ist, der Begriff „Datenbezeichner“ verwendet.
Datenmatrix: In der deutschen Fassung der delegierten
Verordnung wird der Data Matrix Code mit Datenmatrix
übersetzt. Siehe Data Matrix Code.
Delegierte Verordnung: Die delegierte Verordnung
(EU) 2016/161 der Kommission vom 2. Oktober 2015 zur
Ergänzung der Richtlinie 2001/83/EU des Europäischen
Parlaments und des Rates durch die Festlegung genauer Bestimmungen über die Sicherheitsmerkmale auf der
Verpackung von Humanarzneimitteln.
DFI – Data Format Identifier: Definiert welche Ausprägungen der Code nach den ISO-Standard enthält.
Darüber ist festgelegt, welche Datenhülle nach ISO/ IEC
15434, welche Datenbezeichner (AI oder DI), ob ein Makro nach ISO/IEC 16022 und welche Syntax zu verwenden
ist. Derzeit sind als Wert für den DFI „IFA“ oder „GS1“
definiert.
Dot Data Matrix Code: Es handelt sich dabei um einen
Data Matrix Code der aus runden und einzeln stehenden
Punkten aufgebaut ist. Die Data Matrix Norm spezifiziert
keine Dotcode Variante. In der Praxis gibt es aber viele
Dotcode Data Matrix Anwendungen. Es werden dafür
Scanner benötigt, die solche Anwendungen lesen können. In dieser Anwendung, als offenes System,wird auf
die Data Matrix Dotcode Variante verzichtet.
Dotcode: Es handelt sich um eine eigenständige Codeart, die aus einzelnen freistehenden Punkten aufgebaut
ist. Diese Codeart ist hier erwähnt um die Unterscheidung
zwischen dem Dotcode und einen Data Matrix Code in
der Dot Ausführung eindeutig sicherzustellen.
European Medicines Verification Organisation
(EMVO): Die von europäischen Stakeholder-Verbänden
gegründete non-profit Organisation zum Betrieb des Europäischen Hubs (HUB) und zur Anbindung der nationalen Verifikationssysteme (NMVS) an das EMVS.
European Medicines Verification System (EMVS):
Die Systemlandschaft aus dem Europäischen Hub (HUB)
und den angebundenen nationalen Verifikationssystemen (NMVS).
European Medicines Agency (EMA): Europäische Zulassungsbehörde für bestimmte Arzneimittel. Erteilt die
Zulassung für in Europa zentral zugelassene Arzneimittel.
Fälschungsschutzrichtlinie (FMD): Die europäische Richtlinie 2011/62/EU zur Änderung der Richtlinie
2001/83/EG zur Schaffung eines Gemeinschaftskodexes
für Humanarzneimittel hinsichtlich der Verhinderung des
Eindringens von gefälschten Arzneimitteln in die legale
Lieferkette. Die Abkürzung FMD ist aus dem englischen
Begriff (Falsified Medicines Directive) abgeleitet.
Global Trade Item Number (GTIN): Eine weltweit eindeutige Artikelnummer, die in vielen Branchen (FMCG,
Chemie, Gesundheitswesen, Mode, DIY, Rüstungssektor, Banken, etc.) eingesetzt wird. Die GTIN (frühere EAN)
kann in verschiedenen Datenträgern, wie z.B. in einem
Strichcode vom Typ EAN-13 kodiert werden. Andere Kodierungen der GTIN im GS1- 128, Data Matrix Code und
GS1-DataBar sind möglich. Die zuständige IA ist GS1.
GS1 – eingetragenes Warenzeichen: GS1 ist die Abkürzung von Global Standards One, die gemäß ISO/IEC
15459-2 als Ausgabeorganisation (IA) registriert ist und
weltweit die GS1-Nummernsysteme verwaltet.
HIBC – Health Industry Bar Code: Der HIBC ist eine
komprimierte Struktur und wird vornehmlich für die Kennzeichnung von Medizinprodukten verwendet. Der HIBC
wird von dem Systemidentifikator „+“ angeführt, letztem
folgen der alphanumerische, 2–18-stellige Produktcode
sowie die variablen Produktdaten (siehe www.hibc.de).
HIBC ist ebenfalls eine Ausgabeorganisation (IA) die
gemäß ISO/IEC 1549-2 registriert ist und die auch die
Seite 30 All contents copyright © securPharm e.V. | Deutsch V 2.03
Nutzung der Data Identifier (DI) vorsieht.
IFA: IFA Informationsstelle für Arzneispezialitäten GmbH
(www.ifaffm.de). Zuständige Vergabestelle für die PZN
und den PRA-Code für die Nutzung der PPN. Die IFA
ist ebenfalls als Ausgabeorganisation (Issuing Agency)
gemäß ISO/IEC 15459-2 registriert.
Individuelles Erkennungsmerkmal: Gemäß Art. 3 der
delegierten Verordnung (EU) 2016/161 bezeichnet dies
das Sicherheitsmerkmal, das die Überprüfung der Echtheit und die Identifizierung einer Einzelpackung eines
Arzneimittels ermöglicht. In der englischen Fassung wird
dafür der Begriff Unique Identifier verwendet.
Issuing Agency (IA): Eine gemäß ISO/IEC 15459-2 akkreditierte Ausgabeorganisation für Nummernsysteme.
Eine Issuing Agency ist in der Lage, seinen Systemteilnehmern ein System zur weltweit eindeutigen Identifikation von Objekten zur Verfügung zu stellen. Die ISO hat
den Industrieverband AIM beauftragt, als Registration
Authority zu fungieren.
Issuing Agency Code (IAC): Der von der „Registration
Authority for ISO/IEC 15459“ zugeteilte Registration Code
einer Issuing Agency (IA).
Klinikbaustein: Als Klinikbaustein wird eine der Handelspackung gleichende Packung bezeichnet, die allerdings
einzeln nicht verkaufsfähig ist. Dem Klinikbaustein ist eine
PZN zur Identifizierung der Packung zugeordnet, die auf
den Inhalt und die Eigenschaft „Klinikbaustein“ verweist.
Aus gebündelten Klinikbausteinen entstehen Klinikpackungen, denen die für den Handel relevante PZN zugeordnet ist.
Modulgröße: Bezeichnet die idealisierte Größe einer
Matrixzelle im Data Matrix Code.
National Trade Item Number (NTIN): Eine weltweit eindeutige Artikelnummer, in der nationale Artikelnummern
unter Verwendung eines GS1-Präfix’ eingebettet sind. Für
die PZN ist der Präfix „4150“ vergeben. Als Application
Identifier ist wie für die GTIN der AI „01“ zu verwenden.
Analog dazu, ist bei Anwendung des ASC-Formats der
Data Identifier DI „8P“ heranzuziehen.
National Medicines Verification Organisation
(NMVO): Nicht gewinnorientierte Rechtsperson für den
Betrieb des nationalen Verifikationssystems (NMVS). In
Deutschland ist dies securPharm e. V.
National Medicines Verification System (NMVS): Das
nationale Verifikationssystem für einen Mitgliedsstaat.
OTC-Arzneimittel: OTC (engl. over the counter) ist die
Bezeichnung für nicht verschreibungspflichtige Arzneimittel. Gemäß § 48 AMG werden Arzneimittel dann als
nicht verschreibungspflichtig eingeordnet, wenn sie bei
bestimmungsgemäßen Gebrauch die Gesundheit des
Anwenders nicht gefährden, auch wenn sie ohne ärztliche Überwachung angewendet werden. Nicht verschreibungspflichtige Arzneimittel werden noch unterteilt in
apothekenpflichtige und nicht apothekenpflichtige (freiverkäufliche) Arzneimittel.
Pharmacy Product Number (PPN): Eine weltweit
eindeutige Artikelnummer im Gesundheitswesen, in die
nationale Artikelnummern eingebettet sind. Für die PZN
ist der Präfix „11“ als Product Registration Agency Code
vergeben. Der nationalen Artikelnummer (in Deutschland
PZN) folgt die zweistellige Prüfziffer. Als Data Identifier ist
für die PPN der DI „9N“ zu verwenden.
Pharmazeutischer Unternehmer (pU): Nach § 4 Abs.
18 AMG ist pharmazeutischer Unternehmer zum einen
bei zulassungs- und registrierungspflichtigen Arzneimitteln der Inhaber der Zulassung oder Registrierung und
zum anderen derjenige, wer Arzneimittel unter seinem
Namen in Verkehr bringt. Neben dem Zulassungsinhaber
ist damit auch der Mitvertreiber pharmazeutischer Unternehmer, ohne jedoch Inhaber der Zulassung zu sein.
Sowohl der Zulassungsinhaber als auch der Mitvertreiber
können als sogenannte Anbieter bei der IFA PZN für ihre
Arzneimittel beantragen. Im Regelfall beantragt jedoch
nur einer von beiden die PZN und wird damit bei der IFA
zum Anbieter. Dieser Anbieter ist dann auch der Vertragspartner von ACS, dieser ist für das Hochladen der Daten
seiner PZN verantwortlich.
Product Registration Agency-Code (PRACode):
Zweistelliger Präfix zur eindeutigen Kennung einer PPN.
Vergeben und verwaltet von der IFA.
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 31
Produktcode: ist gemäß der delegierten Verordnung
das Sicherheitsmerkmal, auf dem in Verbindung mit der
Seriennummer die Verifikation beruht. Die Kombination aus Produktcode und Seriennummer ist weltweit für
jede Arzneimittelpackung eindeutig. In Deutschland ist
der zur Verifizierung relavante Produktcode die PPN. Im
Data Matrix Code kann der Produktcode im Format der
PPN oder der NTIN ausgegeben werden, die beide die
PZN enthalten.
Pharmazentralnummer (PZN): Nationale Artikelnummer der deutschen, pharmazeutischen Produkte bzw.
apothekenüblichen Waren. Seit 2013 ist die PZN 8-stellig.
Die Vergabe der PZN Nummer ist gesetzlich geregelt und
obliegt der IFA. Die PZN dient dem Handel zur eindeutigen Artikelkennung und wird im Gesundheitswesen für
Abrechnungszwecke genutzt. Siehe http://www.ifaffm.
de/service/index.html. Die entsprechende Nummer in
Österreich wird ebenfalls als PZN bezeichnet. Sie entstammt allerdings einem anderen Nummernkreis, der
von der entsprechenden österreichischen IA verwaltet
wird.
Product Registration Agency (PRA): Vergabestelle
der (nationalen) Artikelnummern, die in Verbindung mit
dem PRA-Code in die PPN überführt werden.
Pseudo Grading: Mit dem Begriff Pseudo Grading wird
eine Bewertung der Druckqualität in Anlehnung an die
Norm ISO/IEC 15415 beschrieben. Diese Methode wird
von Kamerasystemen verwendet, die fest in eine Produktionslinie eingebaut sind und die neben der Lesekontrolle auch Druckqualitätskriterien bestimmen. Da diese
Kamerasysteme keine normierten Messgeräte sind, ist
dem Begriff „Pseudo“ vorangestellt.
Randomisierte Seriennummer: Eine zufällige, nach
einem deterministischen oder nicht-deterministischen
Randomisierungsalgorithmus zu generierende Seriennummer.
Rx-Arzneimittel: Verschreibungspflichtige Arzneimittel
werden im Sprachgebrauch so bezeichnet.
securPharm: Eine Initiative zum Schutz des Patienten
vor gefälschten Arzneimitteln in der legalen Lieferkette in
Deutschland. Sie wird getragen von einem Konsortium
aus Pharma-, Großhandels- und Apothekerverbänden.
securPharm e.V. ist die nicht gewinnorientierte Rechtsperson zum Betrieb des nationalen Verifikationssystems
in Deutschland.
Verifizierung: Unter der Verifizierung wird hier der Prozess der Erkennung von Fälschungen oder Duplikaten
mit Hilfe einer Seriennummer auf Arzneimittelpackungen
verstanden. Im Bereich der optischen Kodierungen wird
der Begriff Verifizierung auch für die Druckqualitätskontrolle der Codes verwendet. Um eine Eindeutigkeit der
Begriffe zu erreichen, wird in der vorliegenden Spezifikation Verifizierung nur in dem Kontext der Fälschungserkennung verwendet. Die Druckqualitätskontrolle wird immer
als Strichcode- oder Matrixcodeprüfung bezeichnet (vgl.
englisch „Barcode verification“ im Sinne der Druckqualitätskontrolle).
XML: Der Begriff ist aus der englischen Bezeichnung
„Extensible Markup Language“ abgeleitet. XML ist eine
Auszeichnungssprache zur Darstellung hierarchisch
strukturierter Daten in Form von Textdaten.
Seite 32 All contents copyright © securPharm e.V. | Deutsch V 2.03
Anhang F
Bibliography
F.1 Normen
ISO 22742: Packaging – Linear bar code and two-dimensional symbols for product packaging
ANSI MH10.8.2: Data Identifier and Application Identifier
Standard
DIN 16587:2015-11: Information technology – Automatic identification and data capture techniques – Data
Matrix Rectangular Extension DIN 16587 Informationstechnik – Automatische Identifikation und Datenerfassungsverfahren – Rechteckige Erweiterung des Data
Matrix-Codes
ISO/IEC 15418: Information technology – Automatic
identification and data capture techniques – GS1 Application Identifiers and ASC MH10 Data Identifiers and
maintenance
Diese Norm referenziert auf ANSI MH10.8.2
ISO/IEC 15415: Information technology – Automatic
identification and data capture techniques – Bar code
print quality test specification – Two-dimensional symbols
ISO/IEC 15434: Information technology – Automatic
identification and data capture techniques – Syntax for
high-capacity ADC media
ISO/IEC 15459-2: Information technology – Unique
identifiers – Part 2: Registration procedures
ISO/IEC 15459-3: Information technology – Unique
identifiers – Part 3: Common rules for unique identifiers
ISO/IEC 16022: Information technology – Automatic
identification and data capture techniques – Data Matrix
bar code symbology specification
ISO/IEC 19762: Information technology – Automatic
identification and data capture (AIDC) techniques – Harmonized vocabulary
ISO 2859-1: Sampling procedures for inspection by attributes Part 1: Sampling plans indexed by acceptable
quality level (AQL) for lot-by-lot inspection
ISO 3951: Sampling procedures and charts for inspection by variables for per cent nonconforming
F.2 Referenz zu Spezifikationen
Die im folgenden aufgeführten Spezifikationen enthalten
die zur Codierung der Handelspackungen notwendigen
Details, im Besonderen die zu den beiden möglichen
Strukturen im Data Matrix Code.:
A Spezifikationen der IFA:
Siehe „Spezifikation PPN-Code – Codierung der Verpackungen mittels Data Matrix Code zum Schutz vor
Arzneimittelfälschungen“: http://www.ifaffm.de/de/ifacodingsystem/data-matrix-handelspackungen.html
Bestandteil des IFA-Coding-System siehe: http://www.
ifa-coding-system.org
B Spezifikationen der GS1:
1.) Identification of Medicines in Germany – NTIN Guideline for use in the securPharm pilot project (https://www.
gs1-germany.de/fileadmin/gs1/basis_informationen/
kennzeichnung_von_pharmazeutika_in_deutschland.
pdf).
2.) Kennzeichnung von Pharmazeutika in Deutschland
– NTIN-Leitfaden für die Verwendung im securPharm-Pilotprojekt (https://www.gs1-germany.de/loesung-fuerfaelschungssichere-arzneien/).
3.) GS1 General Spezification (www.gs1.org).
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 33
Anhang G
Dokumentenhistorie
Version Datum Kategorie
der Änderung Änderung
V 1.0 13.06.2012 Erstausgabe
V 1.01 20.08.2012 Layout-/Textkorrektur Kapitel: 4; 5.1; Anhänge: A; C; H; I (Ergänzung)
V 1.02 05.11.2012 Layout-/Textkorrektur Redaktionelle Änderungen
V 1.03 03.12.2013 Layout-/Textkorrektur Kapitel 4.2;6; Anhang H
V 2.00 15.03.2016 Layout-/Textkorrektur Anforderungen aus der delegierten Verordnung (EU) 2016/161
in entsprechende Kapitel aufgenommen
V 2.01 10.05.2016 Inhalte ergänzt/gestrichen
Kap. 4.5, 5.2.5, 6.4 und 6.6 sowie Anhang E
V 2.02 19.05.2016 Layout-/Textkorrektur Deckblatt, Kap 2, 6.2, Anhang F
V 2.03 05.05.2017 Inhalte ergänzt/gestrichen
Kap. 4.5, 4.6 und 5.3
Seite 34 All contents copyright © securPharm e.V. | Deutsch V 2.03
All contents copyright © securPharm e.V. | Deutsch V 2.03 Seite 35
Impressum
securPharm e.V.
Hamburger Allee 26–28
60486 Frankfurt am Main
Internet: http://www.securPharm.de
Die Inhalte wurden mit größter Sorgfalt erstellt. Sollten
Sie Fehler entdecken oder Inhalte vermissen, so bitten
wir um Ihre Nachricht.
Anmerkung zur Erstellung dieser Spezifikation:
Die Arbeitsgruppe (AG) „Codierung“ von securPharm e.V. hat diese Spezifikation erarbeitet. Dies waren (in alphabetischer Reihenfolge der Familiennamen):
• Dr. Ehrhard Anhalt, Bundesverband der Arzneimittel-Hersteller e.V. (BAH), Bonn
• Martin Bergen, securPharm e.V., Frankfurt/Main
• Michael Borchert, Avoxa – Mediengruppe Deutscher Apotheker GmbH, Eschborn
• Thomas Brückner, Bundesverband der Pharmazeutischen Industrie e.V. (BPI), Berlin
• Michael Dammann, PHAGRO | Bundesverband des Pharmazeutischen Großhandels e.V., Berlin
• Paul Rupp, (Leiter der AG) IFA Informationsstelle für Arzneispezialitäten GmbH, Frankfurt/Main
• Dr. Wolfgang Stock, ACS PharmaProtect GmbH, Berlin
• Wilfried Weigelt, Mitglied im Normenausschuss DIN NA 043-01-31 AA