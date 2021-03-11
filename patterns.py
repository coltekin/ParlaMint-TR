#
# Date/time patterns appear in multiple places
#
date_p = (r"(?P<day>[0-3]?[0-9]) *"
    "(?P<month>Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    "Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık) *"
    "(?P<year>[12][90][0-9][0-9]) *"
    "(?P<dow>Pazartesi|Salı|Çarşamba|Perşembe|Cuma|Cumartesi|Pazar)")

#
# Session number (should only appear in header)
#
sess_p = r"(?P<sessnum>[0-9]+)’[iıuü]nc[ıiuü] Birleşim"

#
# Closing/opening times: occur at the beginning and at the end of
# sittings.
#
begin_p = (r"Açılma [sS]aati ?: *"
    "(?P<starttime>[0-2]?[0-9]\.[0-5][0-9])")
end_p = (r"(?P<timetype>Açılma|Kapanma) [Ss]aati ?: *"
    "(?P<endtime>[0-2]?[0-9]\.[0-5][0-9])")
#
# Sitting (oturum) header.
# 
sitting_p = (r"(?P<sitting>(ON *)?BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|"
    "ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU) OTURUM")
chair_p = (r"BAŞKAN *:  *(?P<chairtype>Geçici Başkan|Başkan Vekili|Başkan)? ?"
        "(?P<chair>(?:[[:upper:]][[:lower:]]+ )+[[:upper:]]+)")
scribe_p = (r"(?:K(?:Â|A)TİP ÜYE(?:LER)? *:)? *"
        "(?P<tempk>Geçici )?Kâtip Üye "
        "(?P<scribe>(?:[[:upper:]][[:lower:][:upper]]+ )+) *"
        " *\((?P<scribe_r>[[:upper:]][[:lower:]]+) ?\),?")
scribe_p += (r"|(?:K(?:Â|A)TİP ÜYE(?:LER)? *:) *"
        "(?P<scribe1>(?:[[:upper:]][[:lower:][:upper:]]+ *)+)"
        " *\((?P<scribe_r1>[[:upper:]][[:lower:]]+) ?\),?"
        "(?: *(?P<scribe2>(?:[[:upper:]][[:lower:][:upper:]]+ *)+)"
        " *\((?P<scribe_r2>[[:upper:]][[:lower:]]+) ?\),?)?")
scribe_p += (r"|(?:Geçici Kâtip Üye) *"
        "(?P<scribe>(?:[[:upper:]][[:lower:][:upper:]]+ *)+)"
        " ?\((?P<scribe_r>[[:upper:]][[:lower:]]+)\),?")
sithend_p = (r"(?P<sithend>---* *(?:0|o) *---*)")
sitstart_p = (r"(?P<sithend2>(?P<spk>BAŞKAN) *(?:–|-) *"
        "(?P<text>(?:(?:Sayın|Saygıdeğer|Değerli).*|[[:upper:]0-9].*açıyorum\.)))")
sitstart_p += (r"|(?P<closed>\(.*[kK]apalıdır|Kapalı Oturum\))")
sithignore_p = (r"K(?:Â|A)TİP ÜYE(?:LER)?: *|.*vmlendif.*|\(Kapalı Oturum\)")

#
# Patterns for maching table of contents 
# 3 levels: first with Roman numerals, second with letters, third with
# Arabric numerals
rm_p = r'(?P<cnum1>(?=[DCLXVI])(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))'
contents1_p = '^' + rm_p + r'\.- *(?P<contdsc1>.*)'
contents2_p = r'^(?P<cnum2>[A-Z])\) *(?P<contdsc2>.*)'
contents3_p = r'^(?P<cnum3>[0-9]+)\.- *(?P<contdsc3>.*)'
contentsX_p = r'(?P<contdscX>.*)'
contents_p = '|'.join((contents1_p,contents2_p,contents3_p))

#
# Misc. patterns to ignore in the header
#
headmisc_p = ('(?P<headmisc>TÜRKİYE BÜYÜK MİLLET MECLİSİ'
              '|TUTANAK DERGİSİ'
              '|İÇİNDEKİLER'
              '|.*Tutanağın sonuna eklidir'
              '|\([Xx]\) .*'
              '|BİRLEŞİM .* SONU'
              '|\(TBMM Tutanak Hizmetleri .*)')

#
# Capture the main utterances/speeches
#
newspk_p = (r"(?P<spkintro>[[:upper:]. ]+ "
             "(?:ADINA|BAŞKANI|SÖZCÜSÜ|BAŞKAN VEKİLİ|BAKANI"
             "|ÜYE|BAŞDENETÇİSİ|YARDIMCISI|BAŞKANVEKİLİ"
             "|ÜYESİ|SÜZCÜSÜ|KOMİSYONU BAŞKAN|KÂTİBİ"
             "|SÖZCÜCÜ|SÖZCÜZÜ|SÖZSÜCÜ|SÖZÜSÜ"
             "|BAŞKANVEKELİ|BAKANLIĞI|CUMHURBAŞKANI) )?"
             "(?P<spk>(?:[[:upper:]. ]+)) "
             "(?:\((?P<spkpar>[\w ]+)\) )?(?:–|-) ?(?P<text>.*)")
paragr_p = (r"(?![[:upper:]. ]+ (?:–|-) )(?P<text>.*)")

