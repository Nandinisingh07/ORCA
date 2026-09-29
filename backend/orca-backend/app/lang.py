"""Language layer (DEMO STUB): script-based detection + fixed templates for en/hi/gu/ta.

This is NOT Bhashini. Production would call Bhashini ASR/translation/TTS; here answers are composed from
hand-written templates so the demo works offline. Have a native speaker review hi/gu/ta strings.
"""
import re

SUPPORTED = ("en", "hi", "gu", "ta")


def detect_language(text: str) -> str:
    counts = {"hi": len(re.findall(r"[\u0900-\u097F]", text)), "gu": len(re.findall(r"[\u0A80-\u0AFF]", text)),
              "ta": len(re.findall(r"[\u0B80-\u0BFF]", text))}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "en"


def norm_lang(s: str | None) -> str | None:
    if not s:
        return None
    t = s.lower().strip()
    if t in ("auto", ""):
        return None
    if t.startswith("hi") or "हिन्दी" in t:
        return "hi"
    if t.startswith("gu") or "ગુજરાતી" in t:
        return "gu"
    if t.startswith("ta") or "தமிழ்" in t:
        return "ta"
    return "en"


T = {
    "en": {
        "days": ["today", "tomorrow", "the day after tomorrow"],
        "greeting": "Good morning, {place}.",
        "head_safe": "{place}, {day}: sea conditions are within the demo safe limits.",
        "head_caution": "{place}, {day}: proceed with caution.",
        "head_unsafe": "{place}, {day}: unsafe conditions are forecast. Avoid going to sea.",
        "head_unknown": "{place}: no forecast data is available, so I cannot give a verdict.",
        "detail": "Highest waves {wave} m, strongest wind {wind} kn (gusts {gust} kn).",
        "tech": "Swell {swell} m, wave period {period} s, sea temperature {sst} °C.",
        "advisory": "Verify with INCOIS and IMD before departure.",
        "eo": "Satellite-derived candidate zones near {place} (chlorophyll observed {date}; heuristic, NOT an INCOIS advisory): {n} zone(s), nearest about {km} km {dir}.",
        "eo_none": "Latest usable satellite chlorophyll near {place} is from {date} and shows no area above the demo threshold, so no candidate zone is suggested.",
        "tide": "Tide (model estimate, not for navigation): {items}.",
        "note_mock": "Note: this answer uses synthetic sample data, not a real forecast.",
        "note_cached": "Note: live data was unavailable; this uses the last saved forecast.",
        "pfz": "Sample fishing-zone guidance for {place} (demo data, not an INCOIS advisory): {n} zone(s), nearest about {km} km {dir} of the landing centre.",
        "boundary": "Nearest demo reference feature: {name}, about {km} km away. Demo boundary layers are illustrative, not legal boundaries.",
        "boundary_inside": "You are inside a demo protected area: {name}.",
        "alerts_n": "{n} condition-based alert(s) for {place}.",
        "alerts_none": "No condition-based alerts for {place}.",
        "route": "Route review: {dist} km {dir} from {place}, highest waves along the route {wave} m.",
        "route_better": "A different heading (about {brg}° {dir}) looks better on the sampled points.",
        "ask_place": "Assuming {place} (default). Tell me your location for a specific answer.",
    },
    "hi": {
        "days": ["आज", "कल", "परसों"],
        "greeting": "सुप्रभात, {place}।",
        "head_safe": "{place}, {day}: समुद्र की स्थिति डेमो की सुरक्षित सीमा के भीतर है।",
        "head_caution": "{place}, {day}: सावधानी के साथ जाएँ।",
        "head_unsafe": "{place}, {day}: खतरनाक स्थिति का पूर्वानुमान है। समुद्र में न जाएँ।",
        "head_unknown": "{place}: पूर्वानुमान डेटा उपलब्ध नहीं है, इसलिए मैं निर्णय नहीं दे सकता।",
        "detail": "सबसे ऊँची लहरें {wave} मीटर, सबसे तेज़ हवा {wind} नॉट (झोंके {gust} नॉट)।",
        "tech": "स्वेल {swell} मी, तरंग अवधि {period} से, समुद्र का तापमान {sst} °C।",
        "advisory": "रवाना होने से पहले INCOIS और IMD से पुष्टि करें।",
        "eo": "{place} के पास उपग्रह-आधारित संभावित क्षेत्र (क्लोरोफिल अवलोकन {date}; अनुमानित विधि, INCOIS की सलाह नहीं): {n} क्षेत्र, सबसे नज़दीकी लगभग {km} किमी {dir}।",
        "eo_none": "{place} के पास सबसे ताज़ा उपयोगी उपग्रह क्लोरोफिल {date} का है और डेमो सीमा से ऊपर कोई क्षेत्र नहीं दिखता, इसलिए कोई संभावित क्षेत्र नहीं सुझाया गया।",
        "tide": "ज्वार-भाटा (मॉडल अनुमान, नौवहन के लिए नहीं): {items}।",
        "note_mock": "ध्यान दें: यह उत्तर नमूना (कृत्रिम) डेटा पर आधारित है, वास्तविक पूर्वानुमान पर नहीं।",
        "note_cached": "ध्यान दें: लाइव डेटा उपलब्ध नहीं था; यह अंतिम सहेजे गए पूर्वानुमान पर आधारित है।",
        "pfz": "{place} के लिए नमूना मत्स्य-क्षेत्र मार्गदर्शन (डेमो डेटा, INCOIS की आधिकारिक सलाह नहीं): {n} क्षेत्र, सबसे नज़दीकी लैंडिंग केंद्र से लगभग {km} किमी {dir}।",
        "boundary": "सबसे नज़दीकी डेमो संदर्भ रेखा/क्षेत्र: {name}, लगभग {km} किमी दूर। डेमो सीमाएँ केवल उदाहरण हैं, कानूनी सीमाएँ नहीं।",
        "boundary_inside": "आप एक डेमो संरक्षित क्षेत्र के अंदर हैं: {name}।",
        "alerts_n": "{place} के लिए स्थिति-आधारित {n} चेतावनी।",
        "alerts_none": "{place} के लिए कोई स्थिति-आधारित चेतावनी नहीं।",
        "route": "मार्ग समीक्षा: {place} से {dist} किमी {dir}, रास्ते में सबसे ऊँची लहरें {wave} मीटर।",
        "route_better": "नमूना बिंदुओं पर एक अलग दिशा (लगभग {brg}° {dir}) बेहतर दिखती है।",
        "ask_place": "{place} मान रहा हूँ (डिफ़ॉल्ट)। सटीक उत्तर के लिए अपना स्थान बताएँ।",
    },
    "gu": {
        "days": ["આજે", "આવતીકાલે", "પરમદિવસે"],
        "greeting": "શુભ સવાર, {place}.",
        "head_safe": "{place}, {day}: દરિયાની સ્થિતિ ડેમોની સલામત મર્યાદામાં છે.",
        "head_caution": "{place}, {day}: સાવચેતી રાખીને જાઓ.",
        "head_unsafe": "{place}, {day}: જોખમી સ્થિતિની આગાહી છે. દરિયામાં જશો નહીં.",
        "head_unknown": "{place}: આગાહીનો ડેટા ઉપલબ્ધ નથી, તેથી હું નિર્ણય આપી શકતો નથી.",
        "detail": "સૌથી ઊંચા મોજાં {wave} મીટર, સૌથી તેજ પવન {wind} નોટ (ઝાટકા {gust} નોટ).",
        "tech": "સ્વેલ {swell} મી, મોજાનો સમયગાળો {period} સેકન્ડ, દરિયાનું તાપમાન {sst} °C.",
        "advisory": "નીકળતા પહેલાં INCOIS અને IMD પાસેથી ખાતરી કરો.",
        "eo": "{place} નજીક ઉપગ્રહ-આધારિત સંભવિત વિસ્તારો (ક્લોરોફિલ અવલોકન {date}; અંદાજિત પદ્ધતિ, INCOISની સલાહ નથી): {n} વિસ્તાર, સૌથી નજીકનો લગભગ {km} કિમી {dir}.",
        "eo_none": "{place} નજીક સૌથી તાજો ઉપયોગી ઉપગ્રહ ક્લોરોફિલ {date}નો છે અને ડેમો મર્યાદાથી ઉપર કોઈ વિસ્તાર દેખાતો નથી, તેથી કોઈ સંભવિત વિસ્તાર સૂચવ્યો નથી.",
        "tide": "ભરતી-ઓટ (મોડેલ અંદાજ, નેવિગેશન માટે નહીં): {items}.",
        "note_mock": "નોંધ: આ જવાબ નમૂનારૂપ (કૃત્રિમ) ડેટા પર આધારિત છે, વાસ્તવિક આગાહી પર નહીં.",
        "note_cached": "નોંધ: લાઇવ ડેટા ઉપલબ્ધ ન હતો; આ છેલ્લે સાચવેલી આગાહી પર આધારિત છે.",
        "pfz": "{place} માટે નમૂનારૂપ માછીમારી-ક્ષેત્ર માર્ગદર્શન (ડેમો ડેટા, INCOISની સત્તાવાર સલાહ નથી): {n} ક્ષેત્ર, લેન્ડિંગ સેન્ટરથી સૌથી નજીકનું લગભગ {km} કિમી {dir}.",
        "boundary": "સૌથી નજીકની ડેમો સંદર્ભ રેખા/વિસ્તાર: {name}, લગભગ {km} કિમી દૂર. ડેમો સીમાઓ માત્ર ઉદાહરણ છે, કાનૂની સીમાઓ નથી.",
        "boundary_inside": "તમે ડેમો સંરક્ષિત વિસ્તારની અંદર છો: {name}.",
        "alerts_n": "{place} માટે સ્થિતિ-આધારિત {n} ચેતવણી.",
        "alerts_none": "{place} માટે કોઈ સ્થિતિ-આધારિત ચેતવણી નથી.",
        "route": "માર્ગ સમીક્ષા: {place}થી {dist} કિમી {dir}, રસ્તામાં સૌથી ઊંચા મોજાં {wave} મીટર.",
        "route_better": "નમૂના બિંદુઓ પર અલગ દિશા (લગભગ {brg}° {dir}) વધુ સારી લાગે છે.",
        "ask_place": "{place} ધારું છું (ડિફૉલ્ટ). ચોક્કસ જવાબ માટે તમારું સ્થાન જણાવો.",
    },
    "ta": {
        "days": ["இன்று", "நாளை", "நாளை மறுநாள்"],
        "greeting": "காலை வணக்கம், {place}.",
        "head_safe": "{place}, {day}: கடல் நிலை டெமோ பாதுகாப்பு வரம்புக்குள் உள்ளது.",
        "head_caution": "{place}, {day}: எச்சரிக்கையுடன் செல்லவும்.",
        "head_unsafe": "{place}, {day}: ஆபத்தான நிலை முன்னறிவிக்கப்பட்டுள்ளது. கடலுக்குச் செல்ல வேண்டாம்.",
        "head_unknown": "{place}: முன்னறிவிப்புத் தரவு இல்லை, எனவே தீர்ப்பு சொல்ல இயலாது.",
        "detail": "அதிகபட்ச அலை உயரம் {wave} மீ, அதிகபட்ச காற்று {wind} நாட் (திடீர் காற்று {gust} நாட்).",
        "tech": "ஸ்வெல் {swell} மீ, அலை காலம் {period} வி, கடல் வெப்பநிலை {sst} °C.",
        "advisory": "புறப்படும் முன் INCOIS மற்றும் IMD-யிடம் உறுதிப்படுத்தவும்.",
        "eo": "{place} அருகே செயற்கைக்கோள் அடிப்படையிலான சாத்தியப் பகுதிகள் (குளோரோபில் கண்காணிப்பு {date}; மதிப்பீட்டு முறை, INCOIS ஆலோசனை அல்ல): {n} பகுதி, அருகில் சுமார் {km} கி.மீ {dir}.",
        "eo_none": "{place} அருகே கிடைத்த சமீபத்திய பயன்படும் செயற்கைக்கோள் குளோரோபில் {date} தேதியது; டெமோ வரம்பை மீறிய பகுதி இல்லை, எனவே சாத்தியப் பகுதி பரிந்துரைக்கப்படவில்லை.",
        "tide": "ஓதம் (மாதிரி மதிப்பீடு, வழிசெலுத்தலுக்கு அல்ல): {items}.",
        "note_mock": "குறிப்பு: இந்தப் பதில் மாதிரி (செயற்கை) தரவை அடிப்படையாகக் கொண்டது, உண்மையான முன்னறிவிப்பு அல்ல.",
        "note_cached": "குறிப்பு: நேரடித் தரவு கிடைக்கவில்லை; கடைசியாகச் சேமித்த முன்னறிவிப்பைப் பயன்படுத்துகிறது.",
        "pfz": "{place}க்கான மாதிரி மீன்பிடி-பகுதி வழிகாட்டல் (டெமோ தரவு, INCOIS அதிகாரப்பூர்வ ஆலோசனை அல்ல): {n} பகுதி, இறங்குதளத்திலிருந்து அருகில் சுமார் {km} கி.மீ {dir}.",
        "boundary": "அருகிலுள்ள டெமோ குறிப்புக் கோடு/பகுதி: {name}, சுமார் {km} கி.மீ தொலைவில். டெமோ எல்லைகள் எடுத்துக்காட்டு மட்டுமே, சட்டப்பூர்வ எல்லைகள் அல்ல.",
        "boundary_inside": "நீங்கள் டெமோ பாதுகாக்கப்பட்ட பகுதிக்குள் உள்ளீர்கள்: {name}.",
        "alerts_n": "{place}க்கு நிலை அடிப்படையிலான {n} எச்சரிக்கை.",
        "alerts_none": "{place}க்கு நிலை அடிப்படையிலான எச்சரிக்கை இல்லை.",
        "route": "பாதை மதிப்பீடு: {place}லிருந்து {dist} கி.மீ {dir}, வழியில் அதிகபட்ச அலை {wave} மீ.",
        "route_better": "மாதிரிப் புள்ளிகளில் வேறு திசை (சுமார் {brg}° {dir}) சிறந்ததாகத் தெரிகிறது.",
        "ask_place": "{place} என எடுத்துக்கொள்கிறேன் (இயல்புநிலை). துல்லியமான பதிலுக்கு உங்கள் இடத்தைச் சொல்லுங்கள்.",
    },
}


def t(lang: str, key: str, **kw) -> str:
    return T.get(lang, T["en"])[key].format(**kw)


def num(v, nd=1) -> str:
    return "—" if v is None else f"{v:.{nd}f}"
