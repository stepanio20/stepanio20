"""German and Czech translations (Katz UI languages). Merged at lookup time."""
from __future__ import annotations

# ---------------------------------------------------------------------------
# T — main message copy. Keys mirror bot/texts.py:T exactly; values are plain
# strings (one language level, merged over T at lookup time). HTML tags,
# {format} placeholders, emojis and line breaks match the ru originals 1:1.
# ---------------------------------------------------------------------------
EXTRA = {
    "de": {
        "choose_lang": "🪙 <b>Katz Coins Radar</b>\n\nSprache wählen / Choose language",
        "welcome": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "Ich behalte die Katz-Auktionen für Sie im Blick:\n\n"
            "🔔 melde Lose zu Ihren Stichwörtern — „Poltina 1859“, „Nicholas II“\n"
            "⏰ erinnere Sie eine Stunde vor Auktionsende\n"
            "📉 zeige, für wie viel Vergleichbares wirklich wegging\n"
            "💼 helfe Ihnen beim Verkauf über Katz\n\n"
            "<b>Was sammeln Sie?</b> Mehrfachauswahl möglich:"
        ),
        "onboarded_hits": "🎯 In den laufenden Katz-Auktionen: <b>{n}</b> Lose zu Ihren Interessen. Hier ein paar davon:",
        "onboarded": (
            "Wunderbar! 🎯 Ihre Interessen sind gespeichert.\n\n"
            "Fangen Sie klein an — mit dem ersten Suchauftrag:\n"
            "<code>/watch Rubel 1912</code>\n\n"
            "oder sehen Sie nach, was gerade versteigert wird: /auctions"
        ),
        "menu": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "Ich fange Lose zu Ihren Suchaufträgen ab, erinnere ans Auktionsende, "
            "zeige erzielte Zuschläge und die Münzvitrine der Mitglieder.\n\n"
            "Einfach unten auf die Buttons tippen 👇"
        ),
        "welcome_back": "🪙 Willkommen zurück! Was schauen wir uns an?",
        "ask_find_query": "🔎 Wonach suchen wir? Schreiben Sie es in einer Nachricht — z. B. <code>Taler 1780</code> oder <code>Nicholas II gold</code>",
        "ask_price_query": "📉 Zu welcher Münze möchten Sie die Zuschlagspreise sehen? Z. B. <code>Poltina 1859</code>",
        "price_empty": ("📉 Im Katz-Archiv gibt es keine Zuschläge zu „{q}“.\n"
                        "Versuchen Sie es kürzer — Typ und Jahr: <code>/price Rubel 1912</code>\n"
                        "Oder stellen Sie das Radar: <code>/watch {q}</code> — ich melde mich, sobald ein Los auftaucht."),
        "cancelled": "✖️ Abgebrochen. Zurück zum Menü 👇",
        "stale_button": "Der Button ist abgelaufen — öffnen Sie /menu",
        "already_watching": "Ist schon auf Ihrem Radar ✅",
        "watch_too_short": ("Der Suchbegriff ist zu kurz — bitte mindestens 3 Zeichen, sonst gäbe es "
                            "zu fast jedem Los einen Alarm. Beispiel: <code>/watch Poltina 1859</code>"),
        "photo_added": "📷 Foto {n}/5 hinzugefügt.",
        "auctions_header": "🏛 <b>Katz-Auktionen — jetzt & demnächst</b>\n━━━━━━━━━━━━━━━",
        "no_auctions": "Noch keine Auktionsdaten — der Parser aktualisiert sie in den nächsten Minuten. Schauen Sie gleich noch einmal vorbei 🙌",
        "watch_usage": (
            "🔭 <b>So legen Sie einen Suchauftrag an</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "<code>/watch Poltina 1859</code>\n"
            "<code>/watch Nicholas II gold &lt;500</code> — mit Preislimit\n\n"
            "Sobald bei Katz ein Los mit diesen Begriffen auftaucht, schicke ich einen Alarm. "
            "Eine Stunde vor Auktionsende erinnere ich Sie zusätzlich."
        ),
        "watch_added": "✅ Suchauftrag angelegt: <b>{q}</b>{cap}\nBelegte Slots: {used}/{total}",
        "watch_limit": (
            "🚦 <b>Alle {total} Radar-Slots sind belegt</b>\n\n"
            "⭐ Pro — 25 Suchaufträge und Erinnerungen 24 h / 1 h\n"
            "🎯 Sniper+ — unbegrenzt viele, plus Alarm 10 Minuten vor Schluss\n\n"
            "👉 /pro · Slot freigeben: /watchlist"
        ),
        "watchlist_header": "🔭 <b>Ihre Suchaufträge</b> ({used}/{total})\n━━━━━━━━━━━━━━━",
        "watchlist_empty": "Noch leer. Legen Sie den ersten an: <code>/watch Rubel 1912</code>",
        "search_usage": "🔎 Suche in den laufenden Auktionen: <code>/find Tscherwonez</code>",
        "search_empty": "Zu „{q}“ läuft gerade nichts. Aufs Radar setzen und den nächsten Treffer nicht verpassen? 👉 <code>/watch {q}</code>",
        "history_usage": "📉 Preisarchiv: <code>/price Rubel Peter</code> — ich zeige, für wie viel ähnliche Lose im Katz-Archiv weggingen.",
        "history_free_teaser": "\n🔒 {shown} von {found} angezeigt. Volle Historie & Export — mit Pro: /pro",
        "alert_match": "🎯 <b>Radar-Treffer für „{q}“</b>",
        "alert_closing": "⏰ <b>In ~1 Stunde endet ein Los von Ihrem Radar</b>",
        "alert_closing10": "🎯 <b>Sniper-Alarm: noch ~10 Minuten bis zum Schluss!</b>",
        "pro_pitch": (
            "⭐ <b>Pro</b> — für Sammler\n"
            "🔔 25 Suchaufträge (statt 3) · Erinnerungen 24 h / 1 h\n"
            "📉 Volle Preishistorie mit Diagramm (Free — 5 Zeilen)\n"
            "🛒 3 Münzen in der Vitrine (statt 1)\n\n"
            "🎯 <b>Sniper+</b> — für Losjäger\n"
            "Alles aus Pro, plus:\n"
            "♾ Unbegrenzte Suchaufträge · Alarm 10 Min vor Schluss\n"
            "🛒 5 Münzen in der Vitrine · bevorzugter Support\n\n"
            "💼 <b>Dealer</b> — für Verkäufer und Händler\n"
            "Alles aus Sniper+, plus:\n"
            "🛒 Bis zu 20 Münzen in der Vitrine, mit Händler-Badge\n"
            "🤝 Bevorzugte Einlieferung zu den Katz-Auktionen\n"
            "📊 Nachfrage-Analysen — bald, für Dealer gratis\n\n"
            "Zahlung in Telegram Stars, verlängert sich automatisch, Kündigung mit einem Tipp."
        ),
        "invoice_title_pro": "Katz Radar Pro — 1 Monat",
        "invoice_title_sniper": "Katz Radar Sniper+ — 1 Monat",
        "invoice_title_dealer": "Katz Radar Dealer — 1 Monat",
        "invoice_desc": "Das Abo verlängert sich automatisch alle 30 Tage. Kündigen können Sie jederzeit in den Telegram-Einstellungen.",
        "paid": "🎉 Zahlung erhalten! Tarif <b>{tier}</b> ist bis {until} aktiv.\nLegen Sie Suchaufträge an: /watch",
        "sell_pitch": (
            "💼 <b>Über Katz Auction verkaufen</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Katz versteigert Monat für Monat Tausende Lose an Käufer aus über 100 Ländern.\n\n"
            "Beschreiben Sie in einer Nachricht, was Sie verkaufen möchten (Land, Nominal, "
            "Jahr, Erhaltung — Fotos gern dazu). "
            "Das Katz-Team meldet sich mit einer Einschätzung.\n\n"
            "Beschreiben Sie die Münze in einer Nachricht ⬇️\n"
            "Anders überlegt? Tippen Sie auf „Abbrechen“ oder /cancel."
        ),
        "sell_thanks": "🤝 Angekommen! Anfrage Nr. {lead_id} ist beim Katz-Team. Eine Antwort kommt meist innerhalb von 1–2 Werktagen.",
        "estimate_start": ("🏷 <b>Schätzung auf Basis der Katz-Zuschläge</b>\n\n"
                           "Beschreiben Sie die Münze in einer Nachricht: Land, Nominal, Jahr, "
                           "Besonderheiten (für eine Verkaufsanfrage gern mit Foto).\n"
                           "Beispiel: <code>Russland Poltina 1859 Alexander II</code>"),
        "estimate_result": ("🏷 <b>Schätzung nach {n} realen Katz-Verkäufen</b>\n"
                            "Typischer Bereich: <b>{p25}–{p75}</b>\n"
                            "Median: <b>{med}</b> · gesamte Spanne {lo}–{hi}\n"
                            "<i>Treffer auf: {words}</i>\n\n"
                            "Ähnliche Zuschläge:\n{comps}\n\n"
                            "💼 Verkaufen? /sell — bei Katz einliefern\n"
                            "🛒 Oder in die Vitrine: /publish"),
        "estimate_none": ("Zu dieser Beschreibung fanden sich im Katz-Archiv keine Vergleichsstücke. "
                          "Versuchen Sie es anders: Land + Nominal + Jahr, ohne Füllwörter. "
                          "Oder holen Sie sich eine persönliche Einschätzung vom Team: /sell"),
        "estimate_quota": ("🚦 Das Schätzungs-Limit Ihres Tarifs ist erreicht ({used}/{quota} pro 30 Tage).\n"
                           "⭐ Pro — 5/Monat · 🎯 Sniper+ — 15 · 💼 Dealer — 30 👉 /pro"),
        "pf_header": "🧺 <b>Sammlungs-Portfolio</b> ({n} Pos.)\nBewertet nach frischen Katz-Zuschlägen:",
        "pf_empty": ("🧺 Das Portfolio ist leer. Fügen Sie die erste Münze hinzu — ich bewerte sie "
                     "nach jeder frischen Katz-Auktion neu."),
        "pf_total": "\nGesamtschätzung: <b>{lo}–{hi}</b> (Mediane: {med}){vs}",
        "pf_vs_buy": " · investiert {buy}",
        "pf_add_ask": ("Beschreiben Sie die Münze (Land, Nominal, Jahr). Auf Wunsch mit Kaufpreis "
                       "am Ende: <code>… for 250</code>"),
        "pf_added": "✅ Ins Portfolio aufgenommen: <b>{title}</b>{buy}",
        "pf_limit": "🚦 Portfolio-Limit in Ihrem Tarif: {limit} Positionen. Mehr — mit Pro: /pro",
        "trial_granted": ("🎁 <b>7 Tage Pro — als Willkommensgeschenk!</b>\n"
                          "25 Radar-Slots und die volle Preishistorie sind schon freigeschaltet. "
                          "Gefällt es Ihnen? /pro verlängert für 299 ⭐/Monat."),
        "referral_reward": "🎉 Ihr Freund hat sein Radar aktiviert — Ihnen wurden <b>+30 Tage Pro</b> gutgeschrieben! Laden Sie weitere ein: /invite",
        "invite": ("🎁 <b>Ein Monat Pro pro Freund</b>\n\n"
                   "Ihr Link:\n{link}\n\n"
                   "Sobald ein Freund den Bot startet und seinen ersten Suchauftrag anlegt, "
                   "bekommen Sie automatisch +30 Tage Pro (bis zu 6 Prämien pro Jahr)."),
        "new_auction": "🏛 <b>Neue Auktion bei Katz!</b>\n{title}\n{lots} Lose · Auktionsstart: {when}",
        "new_auction_hits": "\n🎯 Passend zu Ihren Interessen — <b>{n}</b> Lose",
        "digest_header": "📬 <b>Wochen-Digest</b>\nDie heißesten Lose auf den laufenden Auktionen:",
        "digest_off": "🔕 Digests und Ankündigungen sind aus. Wieder einschalten: /digest",
        "digest_on": "🔔 Digests und Ankündigungen sind an. Ausschalten: /digest",
        "publish_start": (
            "📸 <b>Münze einstellen — Schritt 1 von 4</b>\n\n"
            "Schicken Sie ein Foto der Münze (Avers; im nächsten Schritt können Sie bis zu 5 Fotos ergänzen).\n\n"
            "<i>Gute Fotos verkaufen schneller: Tageslicht, dunkler Hintergrund, beide Seiten.</i>"
        ),
        "publish_photo_ok": ("✅ Foto erhalten.\n\n<b>Schritt 2 von 4.</b> Beschreiben Sie die Münze jetzt in einer Nachricht: "
                             "Land, Nominal, Jahr, Metall, Erhaltung/Grading. Weitere Fotos dürfen gern dazu."),
        "publish_need_photo": "Ohne Foto geht es nicht 📷 — schicken Sie ein Bild der Münze (oder /menu zum Abbrechen).",
        "publish_desc_short": "Zu knapp. Bitte etwas ausführlicher: Land, Nominal, Jahr, Metall, Erhaltung.",
        "publish_price_ask": "<b>Schritt 3 von 4.</b> Welcher Preis in EUR? Schreiben Sie eine Zahl — oder tippen Sie auf „Offen für Angebote“.",
        "publish_price_bad": "Den Preis habe ich nicht verstanden. Schreiben Sie eine Zahl (z. B. <code>150</code>) oder nutzen Sie den Button.",
        "publish_cert_ask": (
            "<b>Schritt 4 von 4 — Verifizierung.</b>\n\n"
            "Steckt die Münze in einem NGC- / PCGS- / PMG-Slab — schicken Sie die Zertifikatsnummer, z. B.:\n"
            "<code>PCGS 45689164</code> oder <code>NGC 6805461-001</code>\n\n"
            "🛡 Wir prüfen im offiziellen Register des Graders: PCGS — automatisch über die "
            "PCGS Public API, NGC/PMG — über die öffentliche Prüfseite + Moderation. "
            "Listings mit bestätigtem Zertifikat bekommen das ✅-Badge und das Vertrauen der Käufer."
        ),
        "publish_cert_bad": ("Das sieht nicht nach einer Zertifikatsnummer aus. Format: <code>PCGS 45689164</code>, "
                             "<code>NGC 6805461-001</code>, <code>PMG 1234567-001</code> — oder „Ohne Zertifikat“."),
        "publish_cert_dup": "⚠️ Dieses Zertifikat gehört schon zu einem aktiven Listing. Ein Slab — ein Listing.",
        "publish_limit": "🚦 Limit aktiver Listings in Ihrem Tarif: {limit}. Mehr Slots — mit Pro/Dealer: /pro",
        "publish_done": ("🎉 <b>Listing #{id} ist online!</b>\n"
                         "Es steht jetzt in der Vitrine /market und wandert in den wöchentlichen Digest. "
                         "Verkauft? Markieren Sie es mit dem Button unter der Karte."),
        "market_header": "🛒 <b>Sammler-Vitrine</b>\nFrische Münzen von Mitgliedern — mit Zertifikatsprüfung:",
        "market_empty": "Die Vitrine ist noch leer. Machen Sie den Anfang: /publish 🪙",
        "market_more": "Mehr anzeigen?",
        "help": (
            "🪙 <b>Befehle</b>\n\n"
            "/auctions — laufende & kommende Auktionen\n"
            "/find — Lose in den laufenden Auktionen suchen\n"
            "/watch — Suchauftrag anlegen\n"
            "/watchlist — mein Radar\n"
            "/price — Zuschlagspreise + Diagramm\n"
            "/market — Münzvitrine der Mitglieder\n"
            "/publish — eigene Münze einstellen (mit Zertifikatsprüfung)\n"
            "/sell — bei Katz einliefern\n"
            "/estimate — Münzschätzung nach dem Zuschlagsarchiv\n"
            "/portfolio — Sammlungs-Portfolio mit Neubewertung\n"
            "/invite — ein Monat Pro pro Freund\n"
            "/digest — Digests an/aus\n"
            "/pro — Tarife · /lang — Sprache"
        ),
    },
    "cs": {
        "choose_lang": "🪙 <b>Katz Coins Radar</b>\n\nZvolte jazyk / Choose language",
        "welcome": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "Hlídám za vás aukce Katz:\n\n"
            "🔔 zachytím položku podle vašich slov — „poltina 1859“, „Nicholas II“\n"
            "⏰ hodinu před koncem dražby pošlu připomínku\n"
            "📉 ukážu, za kolik se podobné kusy skutečně prodávaly\n"
            "💼 pomůžu vám s prodejem přes Katz\n\n"
            "<b>Co sbíráte?</b> Můžete vybrat víc možností:"
        ),
        "onboarded_hits": "🎯 V právě probíhajících aukcích Katz je <b>{n}</b> položek podle vašich zájmů. Pár ukázek:",
        "onboarded": (
            "Výborně! 🎯 Zájmy uloženy.\n\n"
            "Začněte zlehka: přidejte si první hlídání —\n"
            "<code>/watch rubl 1912</code>\n\n"
            "nebo se podívejte, co se právě draží: /auctions"
        ),
        "menu": (
            "🪙 <b>Katz Coins Radar</b>\n\n"
            "Chytám položky podle vašich dotazů, připomínám konec dražby, "
            "ukazuji ceny minulých prodejů i vitrínu mincí členů.\n\n"
            "Stačí ťuknout na tlačítka dole 👇"
        ),
        "welcome_back": "🪙 Vítejte zpátky! Na co se podíváme?",
        "ask_find_query": "🔎 Co v aukcích hledáme? Napište to jednou zprávou — třeba <code>tolar 1780</code> nebo <code>Nicholas II gold</code>",
        "ask_price_query": "📉 U které mince chcete vidět ceny příklepů? Třeba <code>poltina 1859</code>",
        "price_empty": ("📉 V archivu Katz nejsou k „{q}“ žádné prodeje.\n"
                        "Zkuste to stručněji — typ a rok: <code>/price rubl 1912</code>\n"
                        "Nebo si nastavte radar: <code>/watch {q}</code> — ozvu se, jakmile se položka objeví."),
        "cancelled": "✖️ Zrušeno. Vracím vás do menu 👇",
        "stale_button": "Tlačítko už neplatí — otevřete /menu",
        "already_watching": "Už je na radaru ✅",
        "watch_too_short": ("Dotaz je příliš krátký — zadejte aspoň 3 znaky, jinak by upozornění "
                            "chodila skoro na každou položku. Příklad: <code>/watch poltina 1859</code>"),
        "photo_added": "📷 Fotka {n}/5 přidána.",
        "auctions_header": "🏛 <b>Aukce Katz — právě teď a brzy</b>\n━━━━━━━━━━━━━━━",
        "no_auctions": "Zatím tu žádná data o aukcích nejsou — parser je během pár minut doplní. Zkuste to za chviličku 🙌",
        "watch_usage": (
            "🔭 <b>Jak si nastavit hlídání</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "<code>/watch poltina 1859</code>\n"
            "<code>/watch Nicholas II gold &lt;500</code> — s cenovým stropem\n\n"
            "Jakmile se na Katz objeví položka s těmito slovy, pošlu upozornění. "
            "Hodinu před koncem dražby vám dám vědět ještě jednou."
        ),
        "watch_added": "✅ Hlídání přidáno: <b>{q}</b>{cap}\nObsazené sloty: {used}/{total}",
        "watch_limit": (
            "🚦 <b>Všechny {total} sloty radaru jsou obsazené</b>\n\n"
            "⭐ Pro — 25 hlídání a připomínky 24 h / 1 h\n"
            "🎯 Sniper+ — bez limitu a upozornění 10 minut před koncem\n\n"
            "👉 /pro · uvolnit slot: /watchlist"
        ),
        "watchlist_header": "🔭 <b>Vaše hlídání</b> ({used}/{total})\n━━━━━━━━━━━━━━━",
        "watchlist_empty": "Zatím prázdno. Přidejte si první: <code>/watch rubl 1912</code>",
        "search_usage": "🔎 Hledání v probíhajících aukcích: <code>/find červoněc</code>",
        "search_empty": "Na „{q}“ teď v aukcích nic není. Přidat na radar, ať vám nová položka neuteče? 👉 <code>/watch {q}</code>",
        "history_usage": "📉 Historie cen: <code>/price rubl Petr</code> — ukážu, za kolik podobné položky v archivu Katz skutečně odcházely.",
        "history_free_teaser": "\n🔒 Zobrazeno {shown} z {found}. Kompletní historie a export — v Pro: /pro",
        "alert_match": "🎯 <b>Shoda na radaru „{q}“</b>",
        "alert_closing": "⏰ <b>Za ~1 hodinu končí položka z vašeho radaru</b>",
        "alert_closing10": "🎯 <b>Sniper alarm: ~10 minut do konce!</b>",
        "pro_pitch": (
            "⭐ <b>Pro</b> — pro sběratele\n"
            "🔔 25 hlídání (místo 3) · připomínky 24 h / 1 h\n"
            "📉 Kompletní historie cen s grafem (Free — 5 řádků)\n"
            "🛒 3 mince ve vitríně (místo 1)\n\n"
            "🎯 <b>Sniper+</b> — pro lovce položek\n"
            "Vše z Pro a navíc:\n"
            "♾ Hlídání bez limitu · upozornění 10 min před koncem\n"
            "🛒 5 mincí ve vitríně · přednostní podpora\n\n"
            "💼 <b>Dealer</b> — pro prodejce a obchodníky\n"
            "Vše ze Sniper+ a navíc:\n"
            "🛒 Až 20 mincí ve vitríně s odznakem obchodníka\n"
            "🤝 Přednostní příjem položek do aukce Katz\n"
            "📊 Analýza poptávky — již brzy, pro Dealer zdarma\n\n"
            "Platba v Telegram Stars, obnovuje se automaticky, zrušení na jedno ťuknutí."
        ),
        "invoice_title_pro": "Katz Radar Pro — 1 měsíc",
        "invoice_title_sniper": "Katz Radar Sniper+ — 1 měsíc",
        "invoice_title_dealer": "Katz Radar Dealer — 1 měsíc",
        "invoice_desc": "Předplatné se automaticky obnovuje každých 30 dní. Zrušit ho můžete kdykoli v nastavení Telegramu.",
        "paid": "🎉 Platba přijata! Tarif <b>{tier}</b> je aktivní do {until}.\nPřidejte si hlídání: /watch",
        "sell_pitch": (
            "💼 <b>Prodej přes Katz Auction</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Katz měsíčně prodá tisíce položek kupcům z více než 100 zemí.\n\n"
            "Popište jednou zprávou, co chcete prodat (země, nominál, "
            "rok, zachovalost — klidně přiložte fotky). "
            "Tým Katz se vám ozve s oceněním.\n\n"
            "Popište minci jednou zprávou ⬇️\n"
            "Rozmysleli jste si to? Ťukněte na „Zrušit“ nebo /cancel."
        ),
        "sell_thanks": "🤝 Přijato! Žádost č. {lead_id} putuje k týmu Katz. Odpověď obvykle přijde do 1–2 pracovních dnů.",
        "estimate_start": ("🏷 <b>Ocenění podle archivu příklepů Katz</b>\n\n"
                           "Popište minci jednou zprávou: země, nominál, rok, "
                           "zvláštnosti (pro nabídku k prodeji můžete přiložit fotku).\n"
                           "Příklad: <code>Rusko poltina 1859 Alexandr II</code>"),
        "estimate_result": ("🏷 <b>Ocenění podle {n} skutečných prodejů Katz</b>\n"
                            "Typické rozpětí: <b>{p25}–{p75}</b>\n"
                            "Medián: <b>{med}</b> · celkový rozptyl {lo}–{hi}\n"
                            "<i>Podle slov: {words}</i>\n\n"
                            "Podobné příklepy:\n{comps}\n\n"
                            "💼 Chcete prodat? /sell — dát do aukce Katz\n"
                            "🛒 Nebo do vitríny: /publish"),
        "estimate_none": ("K tomuto popisu se v archivu Katz žádné srovnatelné kusy nenašly. "
                          "Zkuste to jinak: země + nominál + rok, bez zbytečných slov. "
                          "Nebo pošlete minci na živé ocenění týmu: /sell"),
        "estimate_quota": ("🚦 Limit ocenění ve vašem tarifu je vyčerpán ({used}/{quota} za 30 dní).\n"
                           "⭐ Pro — 5/měs. · 🎯 Sniper+ — 15 · 💼 Dealer — 30 👉 /pro"),
        "pf_header": "🧺 <b>Portfolio sbírky</b> ({n} poz.)\nOcenění podle čerstvých příklepů Katz:",
        "pf_empty": ("🧺 Portfolio je prázdné. Přidejte první minci — po každé nové aukci Katz "
                     "ji znovu ocením."),
        "pf_total": "\nCelkové ocenění: <b>{lo}–{hi}</b> (mediány: {med}){vs}",
        "pf_vs_buy": " · investováno {buy}",
        "pf_add_ask": ("Popište minci (země, nominál, rok). Chcete-li, připište na konec "
                       "kupní cenu: <code>… for 250</code>"),
        "pf_added": "✅ Přidáno do portfolia: <b>{title}</b>{buy}",
        "pf_limit": "🚦 Limit pozic v portfoliu ve vašem tarifu: {limit}. Víc — v Pro: /pro",
        "trial_granted": ("🎁 <b>7 dní Pro — dárek na uvítanou!</b>\n"
                          "25 slotů radaru a kompletní historie cen jsou už zapnuté. "
                          "Zalíbí se vám? /pro prodlouží za 299 ⭐/měs."),
        "referral_reward": "🎉 Váš přítel si aktivoval radar — připsali jsme vám <b>+30 dní Pro</b>! Pozvěte další: /invite",
        "invite": ("🎁 <b>Měsíc Pro za přítele</b>\n\n"
                   "Váš odkaz:\n{link}\n\n"
                   "Jakmile přítel spustí bota a nastaví si první hlídání, "
                   "automaticky vám přistane +30 dní Pro (až 6 odměn ročně)."),
        "new_auction": "🏛 <b>Nová aukce na Katz!</b>\n{title}\n{lots} položek · start dražby: {when}",
        "new_auction_hits": "\n🎯 Podle vašich zájmů — <b>{n}</b> položek",
        "digest_header": "📬 <b>Týdenní přehled</b>\nNejžhavější položky v právě běžících aukcích:",
        "digest_off": "🔕 Přehledy a oznámení jsou vypnuté. Znovu zapnout: /digest",
        "digest_on": "🔔 Přehledy a oznámení jsou zapnuté. Vypnout: /digest",
        "publish_start": (
            "📸 <b>Vystavení mince — krok 1 ze 4</b>\n\n"
            "Pošlete fotku mince (avers; v dalším kroku můžete přidat až 5 fotek).\n\n"
            "<i>Dobrá fotka = rychlý prodej: denní světlo, tmavé pozadí, obě strany.</i>"
        ),
        "publish_photo_ok": ("✅ Fotka přijata.\n\n<b>Krok 2 ze 4.</b> Teď minci popište jednou zprávou: "
                             "země, nominál, rok, kov, zachovalost/grade. Další fotky můžete klidně přihodit."),
        "publish_need_photo": "Bez fotky to nepůjde 📷 — pošlete snímek mince (nebo /menu pro zrušení).",
        "publish_desc_short": "Moc stručné. Popište to podrobněji: země, nominál, rok, kov, zachovalost.",
        "publish_price_ask": "<b>Krok 3 ze 4.</b> Jaká je cena v EUR? Napište číslo — nebo ťukněte na „Přijímám nabídky“.",
        "publish_price_bad": "Cenu se mi nepodařilo přečíst. Napište číslo (třeba <code>150</code>) nebo použijte tlačítko.",
        "publish_cert_ask": (
            "<b>Krok 4 ze 4 — ověření.</b>\n\n"
            "Pokud je mince ve slabu NGC / PCGS / PMG — pošlete číslo certifikátu, například:\n"
            "<code>PCGS 45689164</code> nebo <code>NGC 6805461-001</code>\n\n"
            "🛡 Ověřujeme v oficiálním registru gradingové společnosti: PCGS — automaticky přes "
            "PCGS Public API, NGC/PMG — přes veřejnou ověřovací stránku + moderaci. "
            "Inzeráty s potvrzeným certifikátem dostanou odznak ✅ a důvěru kupujících."
        ),
        "publish_cert_bad": ("Tohle na číslo certifikátu nevypadá. Formát: <code>PCGS 45689164</code>, "
                             "<code>NGC 6805461-001</code>, <code>PMG 1234567-001</code> — nebo „Bez certifikátu“."),
        "publish_cert_dup": "⚠️ Tento certifikát už patří k aktivnímu inzerátu. Jeden slab — jeden inzerát.",
        "publish_limit": "🚦 Limit aktivních inzerátů ve vašem tarifu: {limit}. Víc slotů — v Pro/Dealer: /pro",
        "publish_done": ("🎉 <b>Inzerát #{id} je zveřejněný!</b>\n"
                         "Najdete ho ve vitríně /market a půjde i do týdenního přehledu. "
                         "Prodáno? Označte to tlačítkem pod kartou."),
        "market_header": "🛒 <b>Vitrína sběratelů</b>\nČerstvé mince od členů — s ověřením certifikátů:",
        "market_empty": "Vitrína je zatím prázdná. Buďte první: /publish 🪙",
        "market_more": "Ukázat další?",
        "help": (
            "🪙 <b>Příkazy</b>\n\n"
            "/auctions — probíhající a nadcházející aukce\n"
            "/find — hledání položek v aukcích\n"
            "/watch — přidat hlídání\n"
            "/watchlist — můj radar\n"
            "/price — ceny příklepů + graf\n"
            "/market — vitrína mincí členů\n"
            "/publish — vystavit vlastní minci (s ověřením certifikátu)\n"
            "/sell — dát do aukce Katz\n"
            "/estimate — ocenění mince podle archivu příklepů\n"
            "/portfolio — portfolio sbírky s přeceňováním\n"
            "/invite — měsíc Pro za přítele\n"
            "/digest — zapnout/vypnout přehledy\n"
            "/pro — tarify · /lang — jazyk"
        ),
    },
}

# ---------------------------------------------------------------------------
# INTERESTS — onboarding interest chips.
# ---------------------------------------------------------------------------
INTERESTS_EXTRA = {
    "de": {
        "ru_imperial": "🇷🇺 Russland & Kaiserreich",
        "world": "🌍 Weltmünzen",
        "ancient": "🏛 Antike",
        "banknotes": "💵 Banknoten",
        "medals": "🎖 Medaillen & Orden",
        "gold": "🥇 Gold / Anlage",
    },
    "cs": {
        "ru_imperial": "🇷🇺 Rusko a carská říše",
        "world": "🌍 Mince světa",
        "ancient": "🏛 Antika",
        "banknotes": "💵 Bankovky",
        "medals": "🎖 Medaile a řády",
        "gold": "🥇 Zlato / investice",
    },
}

# ---------------------------------------------------------------------------
# BTN — reply-keyboard labels (kept <= 20 chars incl. emoji).
# ---------------------------------------------------------------------------
BTN_EXTRA = {
    "de": {
        "auctions": "🏛 Auktionen", "watchlist": "🔭 Mein Radar",
        "find": "🔎 Los finden", "price": "📉 Zuschlagspreise",
        "market": "🛒 Vitrine", "publish": "📤 Münze verkaufen",
        "sell": "💼 Katz-Einlieferung", "pro": "⭐ Pro",
    },
    "cs": {
        "auctions": "🏛 Aukce", "watchlist": "🔭 Můj radar",
        "find": "🔎 Najít položku", "price": "📉 Ceny příklepů",
        "market": "🛒 Vitrína", "publish": "📤 Prodat minci",
        "sell": "💼 Do aukce Katz", "pro": "⭐ Pro",
    },
}

# ---------------------------------------------------------------------------
# COMMANDS — bot command menu (set_my_commands), same order as main.COMMANDS.
# ---------------------------------------------------------------------------
COMMANDS_EXTRA = {
    "de": [
        ("auctions", "🏛 Laufende & kommende Auktionen"),
        ("find", "🔎 Lose in den Auktionen suchen"),
        ("watch", "🔭 Aufs Radar setzen"),
        ("watchlist", "📋 Mein Radar"),
        ("price", "📉 Zuschlagspreise + Diagramm"),
        ("market", "🛒 Münzvitrine der Mitglieder"),
        ("publish", "📤 Eigene Münze einstellen"),
        ("sell", "💼 Bei Katz einliefern"),
        ("estimate", "🏷 Münzschätzung nach Zuschlägen"),
        ("portfolio", "🧺 Sammlungs-Portfolio"),
        ("pro", "⭐ Tarife Pro / Sniper+ / Dealer"),
        ("invite", "🎁 Ein Monat Pro pro Freund"),
        ("digest", "📬 Digests an/aus"),
        ("menu", "🪙 Menü"),
        ("cancel", "✖️ Aktuelle Aktion abbrechen"),
        ("help", "ℹ️ Hilfe"),
    ],
    "cs": [
        ("auctions", "🏛 Probíhající a nadcházející aukce"),
        ("find", "🔎 Hledat položky v aukcích"),
        ("watch", "🔭 Přidat na radar"),
        ("watchlist", "📋 Můj radar"),
        ("price", "📉 Ceny příklepů + graf"),
        ("market", "🛒 Vitrína mincí členů"),
        ("publish", "📤 Vystavit vlastní minci"),
        ("sell", "💼 Dát do aukce Katz"),
        ("estimate", "🏷 Ocenění mince podle příklepů"),
        ("portfolio", "🧺 Portfolio sbírky"),
        ("pro", "⭐ Tarify Pro / Sniper+ / Dealer"),
        ("invite", "🎁 Měsíc Pro za přítele"),
        ("digest", "📬 Zapnout/vypnout přehledy"),
        ("menu", "🪙 Menu"),
        ("cancel", "✖️ Zrušit probíhající akci"),
        ("help", "ℹ️ Nápověda"),
    ],
}


# --- moderation/security keys added after the initial translation pass ----
_PATCH = {
    "de": {
        "publish_done": ("📨 <b>Los #{id} zur Prüfung eingereicht</b>\n"
                         "Wir prüfen Beschreibung und Zertifikat — in der Regel innerhalb "
                         "eines Werktags. Nach der Freigabe erscheint es in /market, "
                         "Sie erhalten eine Benachrichtigung."),
        "publish_approved": "✅ Los #{id} wurde freigegeben und ist jetzt in /market!",
        "publish_need_username": ("Zum Veröffentlichen brauchen Sie einen Telegram-@Benutzernamen — "
                                  "sonst können Käufer Sie nicht erreichen. "
                                  "Einstellungen → Benutzername, dann kommen Sie zurück!"),
        "publish_cooldown": "⏳ Höchstens ein Inserat alle 10 Minuten. Bitte später erneut versuchen.",
        "publish_banned": ("🚫 Veröffentlichen deaktiviert: mehrere Ihrer Inserate wurden abgelehnt. "
                           "Bei einem Irrtum: /paysupport."),
        "paysupport": ("💬 <b>Zahlungs-Support</b>\n\n"
                       "Beschreiben Sie das Problem in einer Nachricht (welcher Tarif, wann bezahlt) — "
                       "wir antworten hier. Stars-Erstattungen folgen den Telegram-Regeln."),
        "paysupport_sent": "🤝 An das Team weitergeleitet. Wir antworten in diesem Chat.",
        "forgetme_confirm": ("⚠️ Alle Ihre Daten löschen: Radar, Portfolio, Inserate, Interessen, "
                             "Verlauf? Zahlungsbelege bleiben aus Buchhaltungsgründen erhalten. "
                             "Das ist unwiderruflich."),
        "forgetme_done": "🗑 Erledigt — alle Daten gelöscht. Danke, dass Sie dabei waren. /start — falls Sie zurückkehren.",
    },
    "cs": {
        "publish_done": ("📨 <b>Položka #{id} odeslána ke schválení</b>\n"
                         "Kontrolujeme popis a certifikát — obvykle do jednoho pracovního dne. "
                         "Po schválení se objeví v /market a přijde vám oznámení."),
        "publish_approved": "✅ Položka #{id} byla schválena a je nyní v /market!",
        "publish_need_username": ("K publikování potřebujete @uživatelské jméno v Telegramu — "
                                  "jinak vás kupující nekontaktují. "
                                  "Nastavení → Uživatelské jméno, pak se vraťte!"),
        "publish_cooldown": "⏳ Nejvýše jedna položka za 10 minut. Zkuste to prosím později.",
        "publish_banned": ("🚫 Publikování je zablokováno: několik vašich položek bylo zamítnuto. "
                           "Pokud jde o omyl: /paysupport."),
        "paysupport": ("💬 <b>Podpora plateb</b>\n\n"
                       "Popište problém jednou zprávou (jaký tarif, kdy zaplaceno) — "
                       "odpovíme zde. Vracení Stars se řídí pravidly Telegramu."),
        "paysupport_sent": "🤝 Předáno týmu. Odpovíme v tomto chatu.",
        "forgetme_confirm": ("⚠️ Smazat všechna vaše data: radar, portfolio, položky, zájmy, "
                             "historii? Platební záznamy zůstávají kvůli účetnictví. "
                             "Tuto akci nelze vrátit."),
        "forgetme_done": "🗑 Hotovo — všechna data smazána. Díky, že jste byli s námi. /start — kdybyste se vrátili.",
    },
}
for _lang, _kv in _PATCH.items():
    EXTRA[_lang].update(_kv)
