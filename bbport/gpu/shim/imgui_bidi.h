// BBSC 2026-11-08: right-to-left lines for Dear ImGui (MIT, as the rest of this folder).
// ImGui draws a line's characters left to right in the order they are stored. A line that holds
// Arabic is handed to ImFont::RenderText in display order instead: its Arabic runs reversed, numbers
// and Latin words kept as they read, punctuation on the side its neighbours give it (a simple form of
// the Unicode bidirectional algorithm, enough for menu texts). The letters arrive already joined
// (Presentation Forms-B: bbport scripts/arabic_shape.py). Included by imgui_draw.cpp only, right before ImFont::RenderText; the build adds the two lines
// (bbport gpu/CMakeLists.txt; the bbhost fork keeps them in its copy).
#pragma once

static inline bool ImBidiIsRtl(unsigned int c)
{
    return (c >= 0x0590 && c <= 0x08FF && !(c >= 0x0660 && c <= 0x0669) && !(c >= 0x06F0 && c <= 0x06F9))
        || (c >= 0xFB1D && c <= 0xFDFF) || (c >= 0xFE70 && c <= 0xFEFF);
}

// 1 strong left-to-right, 2 strong right-to-left, 0 neutral (spaces, punctuation, symbols).
static inline int ImBidiClass(unsigned int c)
{
    if (ImBidiIsRtl(c))
        return 2;
    if ((c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z'))
        return 1;
    if (c >= 0x0660 && c <= 0x0669)
        return 1; // Arabic-Indic digits read left to right as well
    if (c >= 0xC0 && !(c >= 0x2000 && c <= 0x2BFF) && !(c >= 0x3000 && c <= 0x303F) && c != 0xD7 && c != 0xF7)
        return 1; // letters of other scripts, and the button icons (private use)
    return 0;
}

static inline bool ImBidiTextHasRtl(const char* s, const char* e)
{
    // Every right-to-left character is 2 or 3 bytes: lead bytes D6-DF (U+0580-U+07FF), E0 A0-A3 (U+0800-U+08FF), EF AC-BB (U+FB00-U+FEFF).
    for (const unsigned char* p = (const unsigned char*)s; p < (const unsigned char*)e; p++)
        if ((*p >= 0xD6 && *p <= 0xDF) || (*p == 0xEF && p + 1 < (const unsigned char*)e && p[1] >= 0xAC && p[1] <= 0xBB) || (*p == 0xE0 && p + 1 < (const unsigned char*)e && p[1] >= 0xA0 && p[1] <= 0xA3))
        {
            unsigned int c = 0;
            ImTextCharFromUtf8(&c, (const char*)p, e);
            if (ImBidiIsRtl(c))
                return true;
        }
    return false;
}

static inline unsigned int ImBidiMirror(unsigned int c)
{
    switch (c)
    {
    case '(': return ')'; case ')': return '(';
    case '[': return ']'; case ']': return '[';
    case '{': return '}'; case '}': return '{';
    case '<': return '>'; case '>': return '<';
    case 0xAB: return 0xBB; case 0xBB: return 0xAB;
    default: return c;
    }
}

// The line [s, e) in display order, UTF-8, into `out` (cleared first).
static void ImBidiVisualLine(const char* s, const char* e, ImVector<char>& out)
{
    ImVector<unsigned int> cps;
    for (const char* p = s; p < e;)
    {
        unsigned int c = (unsigned char)*p;
        if (c < 0x80) p++;
        else p += ImTextCharFromUtf8(&c, p, e);
        cps.push_back(c);
    }
    const int n = cps.Size;
    ImVector<int> dir; dir.resize(n);
    int base = 0;
    for (int i = 0; i < n; i++)
    {
        dir[i] = ImBidiClass(cps[i]);
        if (!base && dir[i])
            base = dir[i];
    }
    if (!base)
        base = 2;
    // Signs that belong to a number: "50%", "+3", "1.5", "1,000", "12:30", "4/5".
    for (int i = 0; i < n; i++)
        if (dir[i] == 0)
        {
            const unsigned int c = cps[i];
            const bool digit_before = i > 0 && ((cps[i - 1] >= '0' && cps[i - 1] <= '9') || (cps[i - 1] >= 0x0660 && cps[i - 1] <= 0x0669));
            const bool digit_after = i + 1 < n && ((cps[i + 1] >= '0' && cps[i + 1] <= '9') || (cps[i + 1] >= 0x0660 && cps[i + 1] <= 0x0669));
            if ((c == '%' && digit_before) || ((c == '+' || c == '-') && digit_after) || ((c == '.' || c == ',' || c == ':' || c == '/' || c == 0xD7) && digit_before && digit_after))
                dir[i] = 1;
        }
    // A run of neutrals takes its neighbours' direction when both agree, else the line's.
    for (int i = 0; i < n;)
    {
        if (dir[i] != 0) { i++; continue; }
        int j = i;
        while (j < n && dir[j] == 0) j++;
        const int left = i > 0 ? dir[i - 1] : base;
        const int right = j < n ? dir[j] : base;
        const int d = left == right ? left : base;
        for (int k = i; k < j; k++) dir[k] = d;
        i = j;
    }
    // Levels: base right-to-left gives Arabic 1 and the rest 2; base left-to-right gives 0 and 1.
    ImVector<int> level; level.resize(n);
    int top = 0;
    for (int i = 0; i < n; i++)
    {
        level[i] = base == 2 ? (dir[i] == 2 ? 1 : 2) : (dir[i] == 2 ? 1 : 0);
        top = ImMax(top, level[i]);
    }
    ImVector<int> order; order.resize(n);
    for (int i = 0; i < n; i++) order[i] = i;
    for (int lv = top; lv >= 1; lv--)
        for (int i = 0; i < n;)
        {
            if (level[order[i]] < lv) { i++; continue; }
            int j = i;
            while (j < n && level[order[j]] >= lv) j++;
            for (int a = i, b = j - 1; a < b; a++, b--) { int t = order[a]; order[a] = order[b]; order[b] = t; }
            i = j;
        }
    out.resize(0);
    for (int i = 0; i < n; i++)
    {
        unsigned int c = cps[order[i]];
        if (level[order[i]] & 1)
            c = ImBidiMirror(c);
        char buf[5];
        const int len = ImTextCharToUtf8(buf, c);
        for (int k = 0; k < len; k++) out.push_back(buf[k]);
    }
}

// Lines holding Arabic go through ImBidiVisualLine one at a time, each in
// display order; a wrapped paragraph's lines sit against the right edge of the wrap width.
static thread_local bool GImBidiInLine = false;

static void ImBidiRenderText(ImFont* font, ImDrawList* draw_list, float size, const ImVec2& pos, ImU32 col, const ImVec4& clip_rect, const char* text_begin, const char* text_end, float wrap_width, ImDrawTextFlags flags)
{
    ImVector<char> visual;
    float y = pos.y;
    const char* s = text_begin;
    GImBidiInLine = true;
    while (s < text_end && y <= clip_rect.w)
    {
        const char* newline = (const char*)ImMemchr(s, '\n', text_end - s);
        const char* paragraph_end = newline ? newline : text_end;
        const char* line_end = paragraph_end;
        if (wrap_width > 0.0f)
        {
            line_end = ImFontCalcWordWrapPositionEx(font, size, s, paragraph_end, wrap_width, flags);
            if (line_end <= s)
                line_end = s + 1 < paragraph_end ? s + ImTextCountUtf8BytesFromChar(s, paragraph_end) : paragraph_end;
        }
        float x = pos.x;
        if (wrap_width > 0.0f)
            x += ImMax(0.0f, wrap_width - font->CalcTextSizeA(size, FLT_MAX, 0.0f, s, line_end).x);
        if (y + size >= clip_rect.y && line_end > s)
        {
            ImBidiVisualLine(s, line_end, visual);
            if (visual.Size > 0)
                font->RenderText(draw_list, size, ImVec2(x, y), col, clip_rect, visual.Data, visual.Data + visual.Size, 0.0f, flags);
        }
        y += size;
        if (line_end >= paragraph_end)
            s = newline ? newline + 1 : text_end;
        else
            s = ImTextCalcWordWrapNextLineStart(line_end, text_end, flags);
    }
    GImBidiInLine = false;
}

// At the top of ImFont::RenderText (after its label): the one line imgui_draw.cpp gets (gpu/CMakeLists.txt adds it).
#define IMGUI_BIDI_RENDER_TEXT_HOOK \
    if (!GImBidiInLine && ImBidiTextHasRtl(text_begin, text_end ? text_end : text_begin + ImStrlen(text_begin))) \
    { \
        ImBidiRenderText(this, draw_list, size, pos, col, clip_rect, text_begin, text_end ? text_end : text_begin + ImStrlen(text_begin), wrap_width, flags); \
        return; \
    }
