# SPDX-License-Identifier: GPL-2.0-or-later
"""Launcher texts of the low latency setting (NVIDIA Reflex / AMD Anti-Lag 2, vk_low_latency.h), in every
launcher language (see bbport_lang.py). Russian comes from the texts next to the English in
bbport_launcher_win.py."""

LATENCY_KEYS = [
    'Auto (with frame generation)',
    'On + Boost (NVIDIA Reflex only)',
    'Low latency (NVIDIA Reflex / AMD Anti-Lag 2)',
    "The game starts each frame just in time for the graphics card instead of early, so what you press shows "
    "sooner. Auto: on with frame generation, which holds every frame back. Uses whichever the graphics card's "
    "driver offers; also in the game's Graphics menu.",
]

LATENCY = {
    'ar': [
        'تلقائي (مع توليد الإطارات)',
        'تشغيل + Boost (NVIDIA Reflex فقط)',
        'زمن استجابة منخفض (NVIDIA Reflex / AMD Anti-Lag 2)',
        'تبدأ اللعبة كل إطار في الوقت المناسب تمامًا لبطاقة الرسوميات بدلًا من البدء مبكرًا، فيظهر ما تضغطه '
        'أسرع. تلقائي: يعمل مع توليد الإطارات الذي يؤخر كل إطار. يُستخدم ما يوفره برنامج تشغيل بطاقة الرسوميات؛ '
        'وهو موجود أيضًا في قائمة الرسوميات داخل اللعبة.',
    ],
    'es': [
        'Automático (con generación de fotogramas)',
        'Activado + Boost (solo NVIDIA Reflex)',
        'Baja latencia (NVIDIA Reflex / AMD Anti-Lag 2)',
        'El juego empieza cada fotograma justo a tiempo para la tarjeta gráfica en lugar de antes, y lo que '
        'pulsas se ve antes. Automático: activado con la generación de fotogramas, que retiene cada fotograma. '
        'Usa lo que ofrezca el controlador de la tarjeta gráfica; también está en el menú Gráficos del juego.',
    ],
    'pt': [
        'Automático (com geração de quadros)',
        'Ligado + Boost (só NVIDIA Reflex)',
        'Baixa latência (NVIDIA Reflex / AMD Anti-Lag 2)',
        'O jogo começa cada quadro na hora certa para a placa de vídeo, em vez de adiantado, e o que você aperta '
        'aparece antes. Automático: ligado com a geração de quadros, que segura cada quadro. Usa o que o driver '
        'da placa de vídeo oferecer; também está no menu Gráficos do jogo.',
    ],
    'fr': [
        "Auto (avec la génération d'images)",
        'Activé + Boost (NVIDIA Reflex uniquement)',
        'Faible latence (NVIDIA Reflex / AMD Anti-Lag 2)',
        "Le jeu commence chaque image juste à temps pour la carte graphique au lieu d'en avance : ce que vous "
        "appuyez s'affiche plus tôt. Auto : activé avec la génération d'images, qui retient chaque image. Utilise "
        "ce que propose le pilote de la carte graphique ; aussi dans le menu Graphismes du jeu.",
    ],
    'de': [
        'Auto (mit Frame-Generierung)',
        'Ein + Boost (nur NVIDIA Reflex)',
        'Niedrige Latenz (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Das Spiel beginnt jedes Bild gerade rechtzeitig für die Grafikkarte statt zu früh, so erscheint, was du '
        'drückst, früher. Auto: ein mit Frame-Generierung, die jedes Bild zurückhält. Nutzt, was der Treiber der '
        'Grafikkarte anbietet; auch im Grafikmenü des Spiels.',
    ],
    'it': [
        'Auto (con la generazione fotogrammi)',
        'Attivo + Boost (solo NVIDIA Reflex)',
        'Bassa latenza (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Il gioco inizia ogni fotogramma giusto in tempo per la scheda video invece che in anticipo, così ciò che '
        'premi appare prima. Auto: attivo con la generazione fotogrammi, che trattiene ogni fotogramma. Usa ciò che '
        'offre il driver della scheda video; anche nel menu Grafica del gioco.',
    ],
    'pl': [
        'Auto (z generowaniem klatek)',
        'Wł. + Boost (tylko NVIDIA Reflex)',
        'Niskie opóźnienie (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Gra zaczyna każdą klatkę dokładnie na czas dla karty graficznej zamiast z wyprzedzeniem, więc to, co '
        'naciskasz, widać szybciej. Auto: włączone z generowaniem klatek, które wstrzymuje każdą klatkę. Używa '
        'tego, co oferuje sterownik karty graficznej; jest też w menu Grafika w grze.',
    ],
    'tr': [
        'Otomatik (kare oluşturma ile)',
        'Açık + Boost (yalnızca NVIDIA Reflex)',
        'Düşük gecikme (NVIDIA Reflex / AMD Anti-Lag 2)',
        'Oyun her kareye erken değil, ekran kartı için tam zamanında başlar; bastığınız şey daha erken görünür. '
        'Otomatik: her kareyi bekleten kare oluşturma ile açık. Ekran kartı sürücüsünün sunduğunu kullanır; '
        'oyundaki Grafik menüsünde de var.',
    ],
    'zh': [
        '自动（随帧生成开启）',
        '开启 + Boost（仅 NVIDIA Reflex）',
        '低延迟（NVIDIA Reflex / AMD Anti-Lag 2）',
        '游戏不再提前开始每一帧，而是恰好赶上显卡的时机，按键会更早显示在画面上。自动：与会延后每一帧的帧生成一同开启。'
        '使用显卡驱动程序提供的功能；游戏内的图形菜单中也有此选项。',
    ],
    'ja': [
        '自動（フレーム生成と同時）',
        'オン + Boost（NVIDIA Reflex のみ）',
        '低遅延（NVIDIA Reflex / AMD Anti-Lag 2）',
        'ゲームが各フレームを早めではなく、グラフィックカードにちょうど間に合うタイミングで始めるため、操作が画面に早く'
        '反映されます。自動：各フレームを遅らせるフレーム生成と同時にオン。グラフィックカードのドライバーが提供する方式を'
        '使います。ゲーム内のグラフィックメニューにもあります。',
    ],
    'ko': [
        '자동 (프레임 생성과 함께)',
        '켜기 + Boost (NVIDIA Reflex 전용)',
        '낮은 지연 (NVIDIA Reflex / AMD Anti-Lag 2)',
        '게임이 각 프레임을 미리 시작하지 않고 그래픽 카드에 딱 맞춰 시작하므로, 누른 입력이 더 빨리 나타납니다. '
        '자동: 모든 프레임을 붙잡아 두는 프레임 생성과 함께 켜집니다. 그래픽 카드 드라이버가 제공하는 방식을 '
        '사용하며, 게임 내 그래픽 메뉴에도 있습니다.',
    ],
    'th': [
        'อัตโนมัติ (พร้อมการสร้างเฟรม)',
        'เปิด + Boost (เฉพาะ NVIDIA Reflex)',
        'ความหน่วงต่ำ (NVIDIA Reflex / AMD Anti-Lag 2)',
        'เกมจะเริ่มแต่ละเฟรมให้ทันเวลาพอดีกับการ์ดจอแทนที่จะเริ่มก่อน สิ่งที่คุณกดจึงแสดงเร็วขึ้น อัตโนมัติ: เปิดพร้อมการสร้างเฟรม ซึ่งหน่วงทุกเฟรมไว้ ใช้เทคโนโลยีที่ไดรเวอร์การ์ดจอรองรับ และมีในเมนูกราฟิกในเกมด้วย',
    ],
}
