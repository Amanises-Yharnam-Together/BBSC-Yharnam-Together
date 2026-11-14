# SPDX-License-Identifier: GPL-2.0-or-later
"""Launcher texts shown only on Linux (the port built from source or packaged there), in every launcher
language (see bbport_lang.py). Russian comes from the texts next to the English in bbport_launcher_win.py."""

LINUX_KEYS = [
    'DLSS needs {} in {}: {} missing (build.sh copies them when DLSS_SDK_ROOT is set). Until then FSR 3.1 is used.',
    'DLSS uses {} in {} (✓ found). On other GPUs FSR 3.1 is used.',
]

LINUX = {
    'ar': [
        'يحتاج DLSS إلى {} في {}: الناقص {} (ينسخها build.sh عند تعيين DLSS_SDK_ROOT). حتى ذلك الحين يُستخدم FSR 3.1.',
        'يستخدم DLSS الملفات {} في {} (✓ موجودة). على المعالجات الرسومية الأخرى يُستخدم FSR 3.1.',
    ],
    'es': [
        'DLSS necesita {} en {}: faltan {} (build.sh los copia cuando DLSS_SDK_ROOT está definido). Mientras tanto se usa FSR 3.1.',
        'DLSS usa {} en {} (✓ encontrados). En otras GPU se usa FSR 3.1.',
    ],
    'pt': [
        'O DLSS precisa de {} em {}: faltam {} (o build.sh os copia quando DLSS_SDK_ROOT está definido). Até lá, o FSR 3.1 é usado.',
        'O DLSS usa {} em {} (✓ encontrados). Em outras GPUs, o FSR 3.1 é usado.',
    ],
    'fr': [
        'DLSS a besoin de {} dans {} : {} manquant(s) (build.sh les copie quand DLSS_SDK_ROOT est défini). En attendant, FSR 3.1 est utilisé.',
        'DLSS utilise {} dans {} (✓ trouvés). Sur les autres GPU, FSR 3.1 est utilisé.',
    ],
    'de': [
        'DLSS braucht {} in {}: {} fehlen (build.sh kopiert sie, wenn DLSS_SDK_ROOT gesetzt ist). Bis dahin wird FSR 3.1 verwendet.',
        'DLSS nutzt {} in {} (✓ gefunden). Auf anderen GPUs wird FSR 3.1 verwendet.',
    ],
    'it': [
        'DLSS richiede {} in {}: mancano {} (build.sh li copia quando DLSS_SDK_ROOT è impostato). Nel frattempo si usa FSR 3.1.',
        'DLSS usa {} in {} (✓ trovati). Sulle altre GPU si usa FSR 3.1.',
    ],
    'pl': [
        'DLSS potrzebuje {} w {}: brakuje {} (build.sh kopiuje je, gdy ustawiono DLSS_SDK_ROOT). Do tego czasu używany jest FSR 3.1.',
        'DLSS używa {} w {} (✓ znalezione). Na innych GPU używany jest FSR 3.1.',
    ],
    'tr': [
        'DLSS için {} dosyaları {} içinde gerekli: {} eksik (DLSS_SDK_ROOT ayarlıysa build.sh onları kopyalar). O zamana kadar FSR 3.1 kullanılır.',
        'DLSS, {} dosyalarını {} içinde kullanır (✓ bulundu). Diğer GPU’larda FSR 3.1 kullanılır.',
    ],
    'zh': [
        'DLSS 需要 {}（位于 {}）：缺少 {}（设置了 DLSS_SDK_ROOT 时，build.sh 会复制它们）。在此之前使用 FSR 3.1。',
        'DLSS 使用 {}（位于 {}，✓ 已找到）。其他显卡使用 FSR 3.1。',
    ],
    'ja': [
        'DLSS には {} が必要です（場所：{}）：{} が見つかりません（DLSS_SDK_ROOT を設定すると build.sh がコピーします）。それまでは FSR 3.1 を使います。',
        'DLSS は {} を使います（場所：{}、✓ 見つかりました）。ほかの GPU では FSR 3.1 を使います。',
    ],
    'ko': [
        'DLSS에는 {}가 필요합니다(위치: {}): {} 없음(DLSS_SDK_ROOT를 설정하면 build.sh가 복사합니다). 그때까지는 FSR 3.1을 사용합니다.',
        'DLSS는 {}를 사용합니다(위치: {}, ✓ 찾음). 다른 GPU에서는 FSR 3.1을 사용합니다.',
    ],
    'th': [
        'DLSS ต้องใช้ {} ใน {}: ขาด {} (build.sh จะคัดลอกให้เมื่อตั้งค่า DLSS_SDK_ROOT) ระหว่างนี้จะใช้ FSR 3.1',
        'DLSS ใช้ {} ใน {} (✓ พบแล้ว) บน GPU อื่นจะใช้ FSR 3.1',
    ],
}
