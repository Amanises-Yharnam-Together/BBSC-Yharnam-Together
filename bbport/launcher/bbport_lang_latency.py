# SPDX-License-Identifier: GPL-2.0-or-later
"""Launcher texts of the low latency setting (NVIDIA Reflex / AMD Anti-Lag 2, vk_low_latency.h) and of DLSS
frame generation's performance mode, in every
launcher language (see bbport_lang.py). Russian comes from the texts next to the English in
bbport_launcher_win.py."""

LATENCY_KEYS = [
    'Auto (with frame generation)',
    'On + Boost (NVIDIA Reflex only)',
    'Low latency (NVIDIA Reflex / AMD Anti-Lag 2)',
    "The game starts each frame just in time for the graphics card instead of early, so what you press shows "
    "sooner. Auto: on with frame generation, which holds every frame back. Uses whichever the graphics card's "
    "driver offers; also in the game's Graphics menu.",
    'DLSS frame generation: performance mode (preset C)',
    "NVIDIA's lighter frame generation, as preset C in NVIDIA's App: more FPS for the game, a little less detail "
    'in the generated frames. Off: the full model. Takes effect when frame generation starts.',
]

LATENCY = {
    'ar': [
        'تلقائي (مع توليد الإطارات)',
        'تشغيل + Boost (NVIDIA Reflex فقط)',
        'زمن استجابة منخفض (NVIDIA Reflex / AMD Anti-Lag 2)',
        'تبدأ اللعبة كل إطار في الوقت المناسب تمامًا لبطاقة الرسوميات بدلًا من البدء مبكرًا، فيظهر ما تضغطه '
        'أسرع. تلقائي: يعمل مع توليد الإطارات الذي يؤخر كل إطار. يُستخدم ما يوفره برنامج تشغيل بطاقة الرسوميات؛ '
        'وهو موجود أيضًا في قائمة الرسوميات داخل اللعبة.',
        'توليد الإطارات DLSS: وضع الأداء (الإعداد المسبق C)',
        'توليد الإطارات الأخف من NVIDIA، مثل الإعداد المسبق C في تطبيق NVIDIA: إطارات أكثر في الثانية للعبة وتفاصيل أقل قليلًا في الإطارات المولّدة. عند الإيقاف: النموذج الكامل. يسري عند بدء توليد الإطارات.',
    ],
    'es': [
        'Automático (con generación de fotogramas)',
        'Activado + Boost (solo NVIDIA Reflex)',
        'Baja latencia (NVIDIA Reflex / AMD Anti-Lag 2)',
        'El juego empieza cada fotograma justo a tiempo para la tarjeta gráfica en lugar de antes, y lo que '
        'pulsas se ve antes. Automático: activado con la generación de fotogramas, que retiene cada fotograma. '
        'Usa lo que ofrezca el controlador de la tarjeta gráfica; también está en el menú Gráficos del juego.',
        'Generación de fotogramas DLSS: modo rendimiento (preset C)',
        'La generación de fotogramas más ligera de NVIDIA, como el preset C de la app de NVIDIA: más FPS para el juego y un poco menos de detalle en los fotogramas generados. Desactivado: el modelo completo. Se aplica cuando se inicia la generación de fotogramas.',
    ],
    'pt': [
        'Automático (com geração de quadros)',
        'Ligado + Boost (só NVIDIA Reflex)',
        'Baixa latência (NVIDIA Reflex / AMD Anti-Lag 2)',
        'O jogo começa cada quadro na hora certa para a placa de vídeo, em vez de adiantado, e o que você aperta '
        'aparece antes. Automático: ligado com a geração de quadros, que segura cada quadro. Usa o que o driver '
        'da placa de vídeo oferecer; também está no menu Gráficos do jogo.',
        'Geração de quadros DLSS: modo desempenho (preset C)',
        'A geração de quadros mais leve da NVIDIA, como o preset C do app da NVIDIA: mais FPS para o jogo e um pouco menos de detalhe nos quadros gerados. Desligado: o modelo completo. Vale quando a geração de quadros começa.',
    ],
    'fr': [
        "Auto (avec la génération d'images)",
        'Activé + Boost (NVIDIA Reflex uniquement)',
        'Faible latence (NVIDIA Reflex / AMD Anti-Lag 2)',
        "Le jeu commence chaque image juste à temps pour la carte graphique au lieu d'en avance : ce que vous "
        "appuyez s'affiche plus tôt. Auto : activé avec la génération d'images, qui retient chaque image. Utilise "
        "ce que propose le pilote de la carte graphique ; aussi dans le menu Graphismes du jeu.",
        "Génération d'images DLSS : mode performance (préréglage C)",
        "La génération d'images plus légère de NVIDIA, comme le préréglage C de l'application NVIDIA : plus d'images par seconde pour le jeu, un peu moins de détails dans les images générées. Désactivé : le modèle complet. S'applique au démarrage de la génération d'images.",
    ],
    'de': [
        'Auto (mit Frame-Generierung)',
        'Ein + Boost (nur NVIDIA Reflex)',
        'Niedrige Latenz (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Das Spiel beginnt jedes Bild gerade rechtzeitig für die Grafikkarte statt zu früh, so erscheint, was du '
        'drückst, früher. Auto: ein mit Frame-Generierung, die jedes Bild zurückhält. Nutzt, was der Treiber der '
        'Grafikkarte anbietet; auch im Grafikmenü des Spiels.',
        'DLSS-Frame-Generierung: Leistungsmodus (Preset C)',
        'NVIDIAs leichtere Frame-Generierung, wie Preset C in der NVIDIA-App: mehr FPS für das Spiel, etwas weniger Details in den erzeugten Bildern. Aus: das volle Modell. Gilt, wenn die Frame-Generierung startet.',
    ],
    'it': [
        'Auto (con la generazione fotogrammi)',
        'Attivo + Boost (solo NVIDIA Reflex)',
        'Bassa latenza (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Il gioco inizia ogni fotogramma giusto in tempo per la scheda video invece che in anticipo, così ciò che '
        'premi appare prima. Auto: attivo con la generazione fotogrammi, che trattiene ogni fotogramma. Usa ciò che '
        'offre il driver della scheda video; anche nel menu Grafica del gioco.',
        'Generazione fotogrammi DLSS: modalità prestazioni (preset C)',
        "La generazione fotogrammi più leggera di NVIDIA, come il preset C dell'app NVIDIA: più FPS per il gioco, un po' meno dettagli nei fotogrammi generati. Disattivato: il modello completo. Vale all'avvio della generazione fotogrammi.",
    ],
    'pl': [
        'Auto (z generowaniem klatek)',
        'Wł. + Boost (tylko NVIDIA Reflex)',
        'Niskie opóźnienie (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Gra zaczyna każdą klatkę dokładnie na czas dla karty graficznej zamiast z wyprzedzeniem, więc to, co '
        'naciskasz, widać szybciej. Auto: włączone z generowaniem klatek, które wstrzymuje każdą klatkę. Używa '
        'tego, co oferuje sterownik karty graficznej; jest też w menu Grafika w grze.',
        'Generowanie klatek DLSS: tryb wydajności (preset C)',
        'Lżejsze generowanie klatek NVIDIA, jak preset C w aplikacji NVIDIA: więcej FPS w grze, nieco mniej szczegółów w generowanych klatkach. Wył.: pełny model. Działa od uruchomienia generowania klatek.',
    ],
    'tr': [
        'Otomatik (kare oluşturma ile)',
        'Açık + Boost (yalnızca NVIDIA Reflex)',
        'Düşük gecikme (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Oyun her kareye erken değil, ekran kartı için tam zamanında başlar; bastığınız şey daha erken görünür. '
        'Otomatik: her kareyi bekleten kare oluşturma ile açık. Ekran kartı sürücüsünün sunduğunu kullanır; '
        'oyundaki Grafik menüsünde de var.',
        'DLSS kare oluşturma: performans modu (ön ayar C)',
        "NVIDIA'nın daha hafif kare oluşturması, NVIDIA uygulamasındaki ön ayar C gibi: oyun için daha fazla FPS, oluşturulan karelerde biraz daha az ayrıntı. Kapalı: tam model. Kare oluşturma başladığında geçerli olur.",
    ],
    'zh': [
        '自动（随帧生成开启）',
        '开启 + Boost（仅 NVIDIA Reflex）',
        '低延迟（NVIDIA Reflex / AMD Anti-Lag 2）',
        '游戏不再提前开始每一帧，而是恰好赶上显卡的时机，按键会更早显示在画面上。自动：与会延后每一帧的帧生成一同开启。'
        '使用显卡驱动程序提供的功能；游戏内的图形菜单中也有此选项。',
        'DLSS 帧生成：性能模式（预设 C）',
        'NVIDIA 更轻量的帧生成，与 NVIDIA 应用中的预设 C 相同：游戏帧率更高，生成帧的细节略少。关闭：完整模型。在帧生成启动时生效。',
    ],
    'ja': [
        '自動（フレーム生成と同時）',
        'オン + Boost（NVIDIA Reflex のみ）',
        '低遅延（NVIDIA Reflex / AMD Anti-Lag 2）',
        'ゲームが各フレームを早めではなく、グラフィックカードにちょうど間に合うタイミングで始めるため、操作が画面に早く'
        '反映されます。自動：各フレームを遅らせるフレーム生成と同時にオン。グラフィックカードのドライバーが提供する方式を'
        '使います。ゲーム内のグラフィックメニューにもあります。',
        'DLSS フレーム生成：パフォーマンスモード（プリセット C）',
        'NVIDIA アプリのプリセット C と同じ、軽量な NVIDIA のフレーム生成：ゲームの FPS が上がり、生成フレームの細部が少し減ります。オフ：フル モデル。フレーム生成の開始時に適用されます。',
    ],
    'ko': [
        '자동 (프레임 생성과 함께)',
        '켜기 + Boost (NVIDIA Reflex 전용)',
        '낮은 지연 (NVIDIA Reflex / AMD Anti-Lag 2)',
        '게임이 각 프레임을 미리 시작하지 않고 그래픽 카드에 딱 맞춰 시작하므로, 누른 입력이 더 빨리 나타납니다. '
        '자동: 모든 프레임을 붙잡아 두는 프레임 생성과 함께 켜집니다. 그래픽 카드 드라이버가 제공하는 방식을 '
        '사용하며, 게임 내 그래픽 메뉴에도 있습니다.',
        'DLSS 프레임 생성: 성능 모드 (프리셋 C)',
        'NVIDIA 앱의 프리셋 C와 같은 더 가벼운 NVIDIA 프레임 생성: 게임 FPS가 높아지고 생성된 프레임의 디테일이 약간 줄어듭니다. 끄기: 전체 모델. 프레임 생성이 시작될 때 적용됩니다.',
    ],
    'th': [
        'อัตโนมัติ (พร้อมการสร้างเฟรม)',
        'เปิด + Boost (เฉพาะ NVIDIA Reflex)',
        'ความหน่วงต่ำ (NVIDIA Reflex / AMD Anti-Lag 2)',
        'เกมจะเริ่มแต่ละเฟรมให้ทันเวลาพอดีกับการ์ดจอแทนที่จะเริ่มก่อน สิ่งที่คุณกดจึงแสดงเร็วขึ้น อัตโนมัติ: เปิดพร้อมการสร้างเฟรม ซึ่งหน่วงทุกเฟรมไว้ ใช้เทคโนโลยีที่ไดรเวอร์การ์ดจอรองรับ และมีในเมนูกราฟิกในเกมด้วย',
        'การสร้างเฟรม DLSS: โหมดประสิทธิภาพ (พรีเซ็ต C)',
        'การสร้างเฟรมแบบเบากว่าของ NVIDIA เหมือนพรีเซ็ต C ในแอป NVIDIA: เกมได้ FPS มากขึ้น รายละเอียดในเฟรมที่สร้างลดลงเล็กน้อย ปิด: ใช้โมเดลเต็ม มีผลเมื่อการสร้างเฟรมเริ่มทำงาน',
    ],
}
