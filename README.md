# Nota Çevirici

PDF / JPEG nota dosyalarındaki **keman anahtarını (2. çizgide sol)** **alto anahtarına (3. çizgide do)** çevirir ve PDF üretir.
Nota isimleri aynı kalır, her nota bir oktav aşağı yazılır (2. çizgideki sol → 1. ve 2. çizgi arasındaki boşluk).

## Kullanım için gerekenler (Windows 10/11, 64 bit)
1. **Nota Çevirici** kurulum dosyası (`NotaCevirici-Kurulum.exe`).
2. **Audiveris** (nota tanıma). GitHub'da Audiveris sürümler sayfasından Windows kurucusunu indirin.
   Audiveris kurulumu uygun bir **Java** ister (Audiveris 5.3 için Java 17, 5.2 için Java 11).
3. PDF çıktısı için Microsoft **Edge** (Windows'ta hazır gelir) veya Chrome. Yedek olarak MuseScore da kullanılır.

Program Audiveris'i otomatik arar; bulamazsa "Audiveris" satırındaki **Seç...** ile `Audiveris.exe` konumunu gösterin.

## Kullanım
Programı açın → nota dosyasını seçin → **Çevir**. Çıktı PDF'in yanına aynı adla bir `.musicxml` dosyası da kaydedilir;
tanıma hatası varsa bunu MuseScore'da düzeltip tekrar programa verebilirsiniz (MusicXML girdisi Audiveris gerektirmez).

Komut satırı: `NotaCevirici.exe girdi.pdf -o cikti.pdf`

## Sınırlar
- Kalite, nota tanımaya (Audiveris) bağlıdır: temiz, en az 300 dpi taranmış basılı notalarda iyi çalışır; el yazısı veya bozuk taramalarda hata yapar.
- Sadece sade keman anahtarı dönüştürülür; fa anahtarı ve diğerleri olduğu gibi kalır.
- Tiz pasajlar alto anahtarında çok sayıda ek çizgiye çıkabilir.

## Kurulum dosyasını üretmek
**Seçenek 1 (bilgisayarınızda):** Python 3.10+ ve Inno Setup 6 kurun, `build.bat` çalıştırın →
`installer_output\NotaCevirici-Kurulum.exe`.

**Seçenek 2 (hiçbir şey kurmadan):** Bu klasörü bir GitHub deposuna yükleyin; **Actions → Windows kurulum dosyasi → Run workflow**.
İş bitince **Artifacts** bölümünden `NotaCevirici-Kurulum` dosyasını indirin.

Geliştirme: `python main.py` (arayüz) veya `python -m unittest discover -s tests` (testler).
