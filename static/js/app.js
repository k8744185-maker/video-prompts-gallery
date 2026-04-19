// Video Prompts Gallery — Full Cinematic Application

// ─────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────
let appState = {
    prompts: [],
    analytics: [],
    comments: [],
    activeCategory: 'all',
    searchQuery: '',
    currentPage: 1,
    itemsPerPage: 24
};

// Auto-detect if we're running in a Google Site embed or locally
const API_BASE = (window.location.hostname.includes('googleusercontent.com') || window.location.hostname === '') 
    ? 'https://video-prompts-gallery.onrender.com' 
    : '';

/**
 * FETCH WRAPPER FOR GOOGLE SITES
 * When embedded, we MUST include credentials: 'include' for sessions/login to work.
 * This global wrapper ensures all API calls include the necessary cookie-handling flags.
 */
if (window.location.hostname.includes('googleusercontent.com')) {
    const _orgFetch = window.fetch;
    window.fetch = function(url, opts = {}) {
        if (url.toString().startsWith(API_BASE) || url.toString().includes('/api/')) {
            opts.credentials = 'include';
        }
        return _orgFetch(url, opts);
    };
}

// ─────────────────────────────────────────────────────────────
// FIELD MAP  (Google Sheet column names → what we use)
// ─────────────────────────────────────────────────────────────
// Sheet columns: "Unique ID", "Prompt Name", "Category", "Prompt", "Timestamp", "Video ID"
const F_ID = 'Unique ID';
const F_TITLE = 'Prompt Name';
const F_CATEGORY = 'Category';
const F_PROMPT = 'Prompt';
const F_VIDEO_ID = 'Video ID';
const F_AI_TOOL = 'AI Tool';

// ─────────────────────────────────────────────────────────────
// LEGAL CONTENT  (all pages for AdSense compliance)
// ─────────────────────────────────────────────────────────────
const LEGAL_CONTENT = {
    faq: {
        title: 'Frequently Asked Questions',
        content: `
            <h3>What is Video Prompts Gallery?</h3>
            <p>We are a free, curated collection of professional AI video generation prompts designed for filmmakers, creators, and visionaries.</p>

            <h3>Are the prompts free?</h3>
            <p>Yes, all prompts are 100% free to copy and use for personal or commercial projects.</p>

            <h3>Which AI tools are supported?</h3>
            <p>Our prompts work best with Runway Gen-2 / Gen-3, Pika Labs, Kling AI, and Stable Video Diffusion.</p>

            <h3>How do I submit my own prompt?</h3>
            <p>Email us at <a href="mailto:deenavenkat5@gmail.com" style="color:white;">deenavenkat5@gmail.com</a> with the prompt and we'll review it for inclusion.</p>

            <h3>How often are new prompts added?</h3>
            <p>We add new cinematic prompts regularly. Bookmark this page and check back often!</p>
        `
    },
    privacy: {
        title: 'Privacy Policy',
        content: `
            <p><em>Last Updated: March 2026</em></p>

            <h3>1. Information We Collect</h3>
            <p>We do not collect personally identifiable information. We use Google Analytics and Google AdSense, which may collect anonymous browsing data, IP addresses, and cookie identifiers to serve relevant advertising.</p>

            <h3>2. Cookies</h3>
            <p>Our website uses cookies to personalize content and ads, to provide social media features, and to analyse our traffic. By continuing to use this site, you consent to our use of cookies in accordance with this Privacy Policy.</p>

            <h3>3. Google AdSense</h3>
            <p>We use Google AdSense to display advertisements. Google's use of advertising cookies enables it and its partners to serve ads based on your visit to our site and other sites on the Internet. You may opt out of personalised advertising by visiting <a href="https://www.google.com/settings/ads" style="color:white;" target="_blank">Google Ads Settings</a>.</p>

            <h3>4. Third-Party Links</h3>
            <p>Our prompts may reference third-party AI tools. We are not responsible for the privacy practices of those services.</p>

            <h3>5. Contact</h3>
            <p>Questions about privacy? Contact us at <a href="mailto:deenavenkat5@gmail.com" style="color:white;">deenavenkat5@gmail.com</a>.</p>
        `
    },
    terms: {
        title: 'Terms of Service',
        content: `
            <p><em>Last Updated: March 2026</em></p>

            <h3>1. Acceptance of Terms</h3>
            <p>By accessing Video Prompts Gallery, you agree to be bound by these Terms of Service. If you do not agree, please do not use this site.</p>

            <h3>2. License to Use Prompts</h3>
            <p>All prompts are provided under a Creative Commons Zero (CC0) licence. You are free to copy, modify, distribute, and use them, even for commercial purposes, without asking permission.</p>

            <h3>3. Disclaimer</h3>
            <p>The prompts are provided "as is". We make no guarantees about the output produced by any third-party AI model when using our prompts.</p>

            <h3>4. Prohibited Use</h3>
            <p>You may not use this site to distribute spam, malware, or content that infringes third-party intellectual property rights.</p>

            <h3>5. Changes to Terms</h3>
            <p>We reserve the right to modify these Terms at any time. Continued use of the site constitutes acceptance of the updated Terms.</p>
        `
    },
    contact: {
        title: 'Contact Us',
        content: `
            <h3>Get in Touch</h3>
            <p>Have a question, partnership proposal, or a premium prompt to share? We'd love to hear from you.</p>

            <p><strong>📧 Email:</strong> <a href="mailto:deenavenkat5@gmail.com" style="color:white;">deenavenkat5@gmail.com</a></p>
            <p>We typically respond within 24–48 hours on business days.</p>

            <h3>Contribute a Prompt</h3>
            <p>We welcome contributions from the community. Send us your best cinematic prompts and we'll review them for inclusion in the gallery — completely free and credited to you if you wish.</p>

            <h3>Business Enquiries</h3>
            <p>For advertising or sponsorship enquiries, please include "Business" in your email subject line.</p>
        `
    },
    about: {
        title: 'About Video Prompts Gallery',
        content: `
            <h3>Our Mission</h3>
            <p>Video Prompts Gallery is a free, premium collection of cinematic AI video generation prompts. Our goal is to bridge the gap between creative vision and AI execution by providing creators with high-fidelity, production-ready prompts for the world's leading AI video models.</p>

            <h3>What We Offer</h3>
            <p>We provide a curated library of prompts specifically engineered for models like Runway Gen-3, Kling AI, and Pika Labs. Each prompt is tested for consistency, cinematic quality, and artistic merit.</p>
            <ul>
                <li><strong>Cinematic Frameworks:</strong> Prompts that focus on lighting, camera movement, and textures.</li>
                <li><strong>Diverse Categories:</strong> From Sci-Fi and Fantasy to Realistic Nature and Human Emotion.</li>
                <li><strong>Technical Analysis:</strong> Every prompt includes an AI-driven stylistic breakdown to help you understand *why* it works.</li>
                <li><strong>100% Free:</strong> We believe in an open creative ecosystem. All prompts are under CC0 - No rights reserved.</li>
            </ul>

            <h3>Our Technology</h3>
            <p>This gallery is built by filmmakers and engineers who understand the nuances of prompting. We use advanced metadata tagging and a custom-built delivery system on Render to ensure the fastest possible access to your creative tools.</p>
        `
    }
};

// ── AI INSIGHT ENGINE (AdSense 'High Value' Fix) ────────────────
/**
 * Automatically generates a technical breakdown of the prompt to add 
 * unique text content (value) to the page for SEO/AdSense.
 */
function generatePromptInsights(promptText) {
    const p = promptText.toLowerCase();
    let insights = [];
    
    // Lighting Analysis
    if (p.includes('cinematic')) insights.push("<strong>Cinematic Lighting:</strong> This prompt utilizes high-contrast lighting techniques to create a filmic depth and professional look.");
    if (p.includes('golden hour') || p.includes('sunset')) insights.push("<strong>Time of Day:</strong> The choice of golden hour lighting adds natural warmth and long shadows, ideal for emotional storytelling.");
    if (p.includes('neon') || p.includes('cyberpunk')) insights.push("<strong>Color Theory:</strong> Uses a neon-saturated palette to create a high-energy, futuristic atmosphere typical of the cyberpunk genre.");
    
    // Camera / Lens Analysis
    if (p.includes('close up') || p.includes('portrait')) insights.push("<strong>Composition:</strong> Focuses on a tight close-up to emphasize texture and emotional detail, creating an intimate viewer response.");
    if (p.includes('wide shot') || p.includes('landscape')) insights.push("<strong>Visual Scale:</strong> Leverages wide-angle perspectives to establish vastness and environmental scale, perfect for world-building.");
    if (p.includes('drone') || p.includes('aerial')) insights.push("<strong>Perspective:</strong> An aerial view provides a 'Eye in the Sky' perspective, enhancing the sense of grandeur and movement.");
    
    // Mood / Texture
    if (p.includes('grainy') || p.includes('vintage')) insights.push("<strong>Aesthetic:</strong> Incorporates film grain and vintage textures to evoke nostalgia and a 'handcrafted' feel.");
    if (p.includes('hyperrealistic') || p.includes('8k')) insights.push("<strong>Fidelity:</strong> Engineered for maximum detail retention, focusing on micro-textures like skin pores or dust particles.");

    if (p.includes('slow motion')) insights.push("<strong>Temporal Style:</strong> Uses slow-motion dynamics to emphasize poetic movement and allow the viewer to absorb complex visual details.");

    if (insights.length < 2) {
        insights.push("<strong>Artistic Intent:</strong> This prompt is designed to produce a balanced, high-fidelity result suitable for professional creative projects.");
    }
    
    return `
        <div class="insight-container" style="margin-top:1.5rem; padding:1rem; background:rgba(255,255,255,0.03); border-left:3px solid var(--vpg-accent); border-radius:4px;">
            <p style="font-size:0.8rem; text-transform:uppercase; letter-spacing:1px; color:var(--vpg-accent); margin-bottom:0.8rem; font-weight:700;">Stylistic Analysis</p>
            <div style="font-size:0.9rem; color:var(--vpg-text-dim); line-height:1.6;">
                ${insights.map(i => `<p style="margin-bottom:0.8rem;">${i}</p>`).join('')}
                <p style="margin-top:1rem; font-style:italic;"><strong>Pro Tip:</strong> Adjust the camera angle keywords (e.g., 'Low Angle' vs 'Overhead') to completely change the power dynamic of the generated scene.</p>
            </div>
        </div>
    `;
}

// ── JSON-LD Structured Data Generator ────────────────────────────
function injectStructuredData(prompt) {
    // Guard: document.head is null inside Google Sites sandboxed iframes
    if (!document.head) return;
    
    const existing = document.getElementById('vpg-jsonld');
    if (existing) existing.remove();
    
    const script = document.createElement('script');
    script.id = 'vpg-jsonld';
    script.type = 'application/ld+json';
    
    const ld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": prompt[F_TITLE],
        "author": { "@type": "Organization", "name": "Video Prompts Gallery" },
        "description": "Professional AI Video Generation Prompt for " + (prompt[F_AI_TOOL] || 'AI models'),
        "genre": prompt[F_CATEGORY],
        "isAccessibleForFree": "True",
        "publisher": { "@type": "Organization", "name": "Video Prompts Gallery" }
    };
    
    script.text = JSON.stringify(ld);
    document.head.appendChild(script);
}

// ─────────────────────────────────────────────────────────────
// 1. PRELOADER
// ─────────────────────────────────────────────────────────────
function initPreloader() {
    const loader = document.getElementById('vpg-loader');
    const count = document.getElementById('loader-count');
    let pct = 0;

    const interval = setInterval(() => {
        pct += Math.floor(Math.random() * 6) + 2;
        if (pct >= 100) {
            pct = 100;
            clearInterval(interval);
            count.textContent = pct;
            setTimeout(() => {
                loader.classList.add('fade-out');
                setTimeout(() => { loader.style.display = 'none'; }, 800);
            }, 400);
        } else {
            count.textContent = pct;
        }
    }, 35);
}

// ─────────────────────────────────────────────────────────────
// 2. DATA FETCHING
// ─────────────────────────────────────────────────────────────
async function fetchData() {
    try {
        const response = await fetch(API_BASE + '/api/v1/prompts');
        const data = await response.json();
        appState.prompts = data.prompts || [];
        appState.analytics = data.analytics || [];
        appState.comments = data.comments || [];

        renderFilters();
        renderGrid();
        handleRouting();
        logVisit('N/A');
    } catch (error) {
        console.error('Error fetching data:', error);
        showErrorState();
    }
}

function showErrorState() {
    const grid = document.getElementById('prompt-grid');
    if (grid) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:4rem;color:var(--vpg-text-dim);">
            <p style="font-size:1.5rem;margin-bottom:1rem;">⚠️ Could not load prompts</p>
            <p>Please check your connection and <button onclick="location.reload()" style="color:white;background:transparent;border:1px solid white;padding:0.5rem 1rem;cursor:pointer;">Reload</button></p>
        </div>`;
    }
}

async function logVisit(promptId) {
    try {
        await fetch(API_BASE + '/api/v1/analytics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_type: 'visit', prompt_id: promptId })
        });
    } catch (e) { /* silent */ }
}

// ─────────────────────────────────────────────────────────────
// 3. FILTERS & SEARCH
// ─────────────────────────────────────────────────────────────
function renderFilters() {
    const container = document.getElementById('category-filters');
    if (!container) return;
    container.innerHTML = '';

    const rawCategories = appState.prompts.map(p => p[F_CATEGORY]).filter(Boolean);
    const splitCategories = [];
    rawCategories.forEach(cat => {
        cat.split(',').forEach(c => splitCategories.push(c.trim()));
    });
    const uniqueCategories = [...new Set(splitCategories)].sort();

    container.className = 'gallery-filters-scroll'; // Change class for horizontal scroll

    const createPill = (txt, val) => {
        const btn = document.createElement('button');
        btn.className = 'filter-pill' + (appState.activeCategory === val ? ' active' : '');
        btn.textContent = txt;
        btn.onclick = () => setCategory(val);
        return btn;
    };

    container.appendChild(createPill('All', 'all'));
    uniqueCategories.forEach(cat => container.appendChild(createPill(cat, cat)));
}

let _searchTimeout;
function debounceSearch() {
    clearTimeout(_searchTimeout);
    _searchTimeout = setTimeout(() => {
        const q = (document.getElementById('vpg-search-input') || {}).value || '';
        appState.searchQuery = q.trim().toLowerCase();
        appState.currentPage = 1;
        renderGrid();
    }, 280);
}

function setCategory(cat) {
    appState.activeCategory = cat;
    appState.currentPage = 1;
    renderGrid();
}

// ─────────────────────────────────────────────────────────────
// 4. GRID RENDERING
// ─────────────────────────────────────────────────────────────
function renderGrid() {
    const grid = document.getElementById('prompt-grid');
    if (!grid) return;
    grid.innerHTML = '';

    // Sort by Video ID numerically: video_001 < video_002 < ... < no-id (end)
    const parseVideoNum = (p) => {
        const vid = (p[F_VIDEO_ID] || '').trim();
        const match = vid.match(/(\d+)$/);
        return match ? parseInt(match[1], 10) : Infinity;
    };
    let filtered = [...appState.prompts].sort((a, b) => parseVideoNum(a) - parseVideoNum(b));

    if (appState.activeCategory !== 'all') {
        filtered = filtered.filter(p => {
            const promptCats = (p[F_CATEGORY] || '').split(',').map(c => c.trim().toLowerCase());
            return promptCats.includes(appState.activeCategory.toLowerCase());
        });
    }

    if (appState.searchQuery) {
        filtered = filtered.filter(p =>
            (p[F_TITLE] || '').toLowerCase().includes(appState.searchQuery) ||
            (p[F_PROMPT] || '').toLowerCase().includes(appState.searchQuery) ||
            (p[F_CATEGORY] || '').toLowerCase().includes(appState.searchQuery)
        );
    }

    const totalPages = Math.max(1, Math.ceil(filtered.length / appState.itemsPerPage));
    if (appState.currentPage > totalPages) appState.currentPage = 1;

    const start = (appState.currentPage - 1) * appState.itemsPerPage;
    const paginated = filtered.slice(start, start + appState.itemsPerPage);

    if (paginated.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:5rem 2rem;color:var(--vpg-text-dim);">
            <p style="font-size:1.4rem;font-family:'Playfair Display',serif;">No prompts found</p>
            <p style="margin-top:0.5rem;">Try a different search term or category.</p>
        </div>`;
        renderPagination(0);
        return;
    }

    paginated.forEach((prompt, i) => {
        // Insert ad placeholder after item 5 (position 6)
        if (i === 5) {
            grid.appendChild(makeAdCard());
        }
        grid.appendChild(makePromptCard(prompt));
    });

    renderPagination(totalPages);
}

function makeAdCard() {
    const div = document.createElement('div');
    div.className = 'vpg-card ad-card';
    div.innerHTML = `
        <div class="vpg-card-tag">Sponsor</div>
        <ins class="adsbygoogle"
             style="display:block;min-height:200px;"
             data-ad-format="fluid"
             data-ad-layout-key="-fb+5w+4e-db+86"
             data-ad-client="ca-pub-5050768956635718"
             data-ad-slot="4127739184"></ins>
        <script>(adsbygoogle = window.adsbygoogle || []).push({});<\/script>
    `;
    return div;
}

function makePromptCard(prompt) {
    const id = prompt[F_ID] || '';
    const title = prompt[F_TITLE] || 'Untitled';
    const imageUrl = prompt['Image URL'] || '';

    const card = document.createElement('div');
    card.className = 'vpg-card';
    card.dataset.promptId = id;

    if (imageUrl) {
        const img = document.createElement('img');
        img.src = imageUrl;
        img.className = 'vpg-card-img';
        img.alt = title;
        img.loading = 'lazy';
        img.style.opacity = '0';
        img.style.transition = 'opacity 0.4s ease-in-out';
        img.onload = () => {
            img.style.opacity = '1';
            card.style.animation = 'none';
        };
        img.onerror = () => {
            img.style.display = 'none';
            const errorFallback = el('div', 'vpg-card-fallback', title);
            card.prepend(errorFallback);
            card.style.animation = 'none';
        };
        card.appendChild(img);

        const overlay = document.createElement('div');
        overlay.className = 'vpg-card-overlay';

        const badge = document.createElement('div');
        badge.className = 'vpg-get-prompt-btn';
        badge.innerHTML = '✨ Get Prompt';

        const titleText = document.createElement('div');
        titleText.className = 'vpg-card-hover-title';
        titleText.textContent = title;

        overlay.appendChild(badge);
        overlay.appendChild(titleText);
        card.appendChild(overlay);
    } else {
        const fallback = el('div', 'vpg-card-fallback', title);
        card.appendChild(fallback);
    }

    card.addEventListener('click', () => showDetail(id));

    return card;
}

/** Utility: create element with class + textContent */
function el(tag, cls, text) {
    const e = document.createElement(tag);
    e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
}

// ─────────────────────────────────────────────────────────────
// 5. PAGINATION
// ─────────────────────────────────────────────────────────────
function renderPagination(total) {
    const container = document.getElementById('vpg-pagination');
    if (!container) return;
    container.innerHTML = '';
    if (total <= 1) return;

    for (let i = 1; i <= total; i++) {
        const btn = document.createElement('button');
        btn.className = 'page-btn' + (i === appState.currentPage ? ' active' : '');
        btn.textContent = i;
        btn.addEventListener('click', () => {
            appState.currentPage = i;
            renderGrid();
            const search = document.getElementById('vpg-search');
            if (search) window.scrollTo({ top: search.offsetTop - 100, behavior: 'smooth' });
        });
        container.appendChild(btn);
    }
}

// ─────────────────────────────────────────────────────────────
// 6. DETAIL MODAL
// ─────────────────────────────────────────────────────────────
function showDetail(id) {
    const prompt = appState.prompts.find(p => p[F_ID] == id);
    if (!prompt) {
        console.warn('Prompt not found:', id);
        return;
    }

    const title = prompt[F_TITLE] || 'Untitled';
    const category = prompt[F_CATEGORY] || 'General';
    const text = prompt[F_PROMPT] || '';
    const imageUrl = prompt['Image URL'] || '';
    const likes = (appState.analytics || []).filter(
        a => a['Prompt ID'] == id && a['Event Type'] === 'like'
    ).length;

    const modal = document.getElementById('vpg-modal');
    const body = document.getElementById('modal-body');
    if (!modal || !body) return;

    body.innerHTML = '';

    if (imageUrl) {
        const img = document.createElement('img');
        img.src = imageUrl;
        img.className = 'modal-detail-img';
        img.alt = title;
        body.appendChild(img);
    }

    const aiToolRaw = (prompt[F_AI_TOOL] || 'gemini').toLowerCase();
    let toolName = 'Gemini';
    let toolUrl = 'https://gemini.google.com';
    let toolColor = '#8b5cf6'; // Solid purple/blue instead of invalid css var

    if (aiToolRaw.includes('chatgpt')) {
        toolName = 'ChatGPT';
        toolUrl = 'https://chatgpt.com';
        toolColor = '#10a37f'; // ChatGPT green
    } else if (aiToolRaw.includes('runway')) {
        toolName = 'Runway ML';
        toolUrl = 'https://runwayml.com';
    } else if (aiToolRaw.includes('pika')) {
        toolName = 'Pika Labs';
        toolUrl = 'https://pika.art';
    } else if (aiToolRaw.includes('kling')) {
        toolName = 'Kling AI';
        toolUrl = 'https://klingai.com';
    } else if (aiToolRaw.includes('midjourney')) {
        toolName = 'Midjourney';
        toolUrl = 'https://midjourney.com';
    }

    // Tags Row
    const tagsRow = el('div', 'modal-tag-row');
    tagsRow.innerHTML = `
        <div class="modal-tag-pill" style="color: ${toolColor}; border-color: ${toolColor}40;">✨ ${toolName}</div>
        <div class="modal-tag-pill">🏷️ ${category.split(',')[0]}</div>
    `;
    body.appendChild(tagsRow);

    // Action Row (Fav, Share)
    const actionRow = el('div', 'modal-action-row');

    const favBtn = el('button', 'btn-detail-action');
    favBtn.id = `modal-like-btn-${id}`;
    favBtn.innerHTML = `♡ Favorite  ${likes > 0 ? `(${likes})` : ''}`;
    favBtn.onclick = () => handleLike(id, favBtn);

    const shareBtn = el('button', 'btn-detail-action');
    shareBtn.innerHTML = `↗ Share`;
    shareBtn.onclick = () => sharePrompt(id);

    actionRow.append(favBtn, shareBtn);
    body.appendChild(actionRow);

    // Main Copy & Open button
    const copyOpenBtn = el('button', 'btn-detail-copy');
    copyOpenBtn.innerHTML = `✨ COPY & OPEN ${toolName.toUpperCase()}`;
    copyOpenBtn.style.backgroundColor = toolColor;
    copyOpenBtn.onclick = () => {
        copyPrompt(id, false);
        showCopyOverlay(toolName, toolUrl);
    };
    body.appendChild(copyOpenBtn);

    // Prompt Box
    const prLabel = el('div', 'modal-prompt-label', 'PROMPT');
    body.appendChild(prLabel);

    const prBox = el('div', 'modal-prompt-box');
    prBox.textContent = text;
    body.appendChild(prBox);

    // Admin-Only Controls
    if (adminState && adminState.isAdmin) {
        const editModalBtn = document.createElement('button');
        editModalBtn.className = 'btn-detail-action';
        editModalBtn.style.width = '100%';
        editModalBtn.style.marginBottom = '2rem';
        editModalBtn.textContent = '✏️ Edit Prompt';
        editModalBtn.addEventListener('click', () => { closeModal(); openEditPrompt(id); });
        body.appendChild(editModalBtn);
    }

    // Related Prompts Section
    renderRelatedPrompts(body, id, category);

    // Final footer row in body
    const promptInsightHTML = generatePromptInsights(text);
    const insightWrap = el('div');
    insightWrap.innerHTML = promptInsightHTML;
    body.appendChild(insightWrap);

    // Inject Search Engine Data
    injectStructuredData(prompt);

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    document.title = `${title} — Video Prompts Gallery`;

    // Self-referencing canonical for deep links
    _setCanonical(`https://video-prompts-gallery.onrender.com/?prompt_id=${id}`);

    logVisit(id);
}

function renderRelatedPrompts(container, currentId, currentCategory) {
    const mainCategory = currentCategory.split(',')[0].trim();
    
    // Find up to 3 prompts in the same category, excluding the current one
    let related = appState.prompts.filter(p => 
        p[F_ID] !== currentId && 
        p[F_CATEGORY] && 
        p[F_CATEGORY].includes(mainCategory)
    ).slice(0, 3);

    // If we couldn't find enough, grab a few random ones
    if (related.length < 3) {
        const others = appState.prompts.filter(p => p[F_ID] !== currentId && !related.includes(p));
        const needed = 3 - related.length;
        related = related.concat(others.slice(0, needed));
    }

    if (related.length === 0) return;

    const relatedWrapper = el('div', 'modal-related-wrapper');
    relatedWrapper.innerHTML = `
        <h4 style="margin-top: 2.5rem; margin-bottom: 1rem; font-family: 'Playfair Display', serif; font-size: 1.2rem; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1.5rem;">You might also like</h4>
        <div class="modal-related-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;"></div>
    `;
    
    const gridEl = relatedWrapper.querySelector('.modal-related-grid');
    
    related.forEach(prompt => {
        const card = el('div', 'modal-related-card');
        card.style.cursor = 'pointer';
        card.style.background = 'rgba(255,255,255,0.03)';
        card.style.border = '1px solid rgba(255,255,255,0.08)';
        card.style.borderRadius = '8px';
        card.style.overflow = 'hidden';
        card.style.transition = 'background 0.2s, transform 0.2s';
        
        card.onclick = () => {
            // Scroll to top of modal when clicking a related prompt
            const modalBody = document.querySelector('.modal-content');
            if (modalBody) modalBody.scrollTop = 0;
            showDetail(prompt[F_ID]);
        };

        // Hover effects inline for simplicity, or we can just rely on pure CSS classes.
        // Let's use simple HTML content.
        const imgUrl = prompt['Image URL'] || 'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=400&q=80';
        
        card.innerHTML = `
            <img src="${imgUrl}" alt="Related prompt" style="width: 100%; height: 120px; object-fit: cover;">
            <div style="padding: 0.8rem;">
                <div style="font-size: 0.65rem; color: #a855f7; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.3rem;">${prompt[F_CATEGORY].split(',')[0]}</div>
                <div style="font-family: 'Playfair Display', serif; font-size: 0.95rem; line-height: 1.3; margin-bottom: 0;">${prompt[F_TITLE].substring(0, 40)}${prompt[F_TITLE].length > 40 ? '...' : ''}</div>
            </div>
        `;
        
        card.onmouseover = () => card.style.background = 'rgba(255,255,255,0.07)';
        card.onmouseout = () => card.style.background = 'rgba(255,255,255,0.03)';

        gridEl.appendChild(card);
    });

    container.appendChild(relatedWrapper);
}

function closeModal() {
    const m = document.getElementById('vpg-modal');
    if (m) m.classList.add('hidden');
    document.body.style.overflow = '';
    document.title = 'Video Prompts Gallery — Cinematic AI Prompt Collection';

    // Restore homepage canonical
    _setCanonical('https://video-prompts-gallery.onrender.com/');
}

// ─────────────────────────────────────────────────────────────
// 7. ACTIONS (Like, Copy, Share)
// ─────────────────────────────────────────────────────────────
async function handleLike(id, btn) {
    if (!btn || btn.disabled) return;
    btn.disabled = true;
    btn.textContent = 'Liking…';

    try {
        const res = await fetch(API_BASE + '/api/v1/interaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'like', prompt_id: id })
        });

        if (res.ok) {
            btn.textContent = '♥ Liked!';
            // Update local analytics state so count reflects immediately
            appState.analytics.push({ 'Prompt ID': id, 'Event Type': 'like' });
            // Update card like button count if visible
            const cardBtn = document.getElementById(`like-btn-${id}`);
            if (cardBtn) {
                const n = (appState.analytics || []).filter(
                    a => a['Prompt ID'] == id && a['Event Type'] === 'like'
                ).length;
                cardBtn.textContent = `♥ Like (${n})`;
            }
        } else {
            btn.disabled = false;
            btn.textContent = '♥ Like';
        }
    } catch (e) {
        btn.disabled = false;
        btn.textContent = '♥ Like';
    }
}

function copyPrompt(id, showUserToast = true) {
    const prompt = appState.prompts.find(p => p[F_ID] == id);
    if (!prompt) return;

    const text = prompt[F_PROMPT] || '';

    const succeed = () => {
        if (showUserToast) showToast('🔗 Copied!');
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(succeed).catch(() => fallbackCopy(text, succeed));
    } else {
        fallbackCopy(text, succeed);
    }
}

function showCopyOverlay(toolName, toolUrl) {
    let overlay = document.getElementById('vpg-copy-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'vpg-copy-overlay';
        document.body.appendChild(overlay);
    }
    
    // Always rebuild inner HTML so tool Name & URL updates dynamically
    overlay.innerHTML = `
        <div class="copy-overlay-card">
            <div class="copy-overlay-icon">✨</div>
            <div class="copy-overlay-title">You got your prompt!</div>
            <div class="copy-overlay-text">Add your image with the copied prompt to get the result.</div>
            <button class="btn-overlay-open" onclick="window.open('${toolUrl}', '_blank'); hideCopyOverlay()">✨ OPEN ${toolName.toUpperCase()}</button>
            <button class="btn-overlay-later" onclick="hideCopyOverlay()">Maybe Later</button>
        </div>
    `;
    overlay.classList.add('show');
}

function hideCopyOverlay() {
    const o = document.getElementById('vpg-copy-overlay');
    if (o) o.classList.remove('show');
}

function fallbackCopy(text, cb) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0;top:-9999px;';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); cb(); } catch (e) { }
    document.body.removeChild(ta);
}

function sharePrompt(id) {
    // Attempt to detect the parent page URL (Google Sites page) via document.referrer
    // If not available or irrelevant, fall back to API_BASE or current location.
    let base = window.SHARE_BASE_URL;
    
    if (!base) {
        const referrer = document.referrer;
        if (referrer && (referrer.includes('sites.google.com') || referrer.includes('googleusercontent.com'))) {
            // Use the referrer but strip the path to just the page if needed? 
            // Actually, referrer is the exact page URL.
            base = referrer.split('?')[0].split('#')[0];
        } else {
            // Avoid hardcoding onrender unless we are literally on onrender
            if (location.hostname.includes('onrender.com')) {
                base = 'https://video-prompts-gallery.onrender.com/';
            } else {
                // This covers Vercel, Netlify, Custom Domains, or direct file access
                base = location.origin !== 'null' ? (location.origin + location.pathname) : 'https://sites.google.com/'; 
            }
        }
    }
    
    const url = `${base.replace(/\/$/, '')}/?prompt_id=${encodeURIComponent(id)}`;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
            showToast('🔗 Share link copied to clipboard!');
        }).catch(() => fallbackCopy(url, () => showToast('🔗 Link copied!')));
    } else {
        fallbackCopy(url, () => showToast('🔗 Link copied!'));
    }
}

function showToast(msg) {
    let t = document.getElementById('vpg-toast');
    if (!t) {
        t = document.createElement('div');
        t.id = 'vpg-toast';
        t.style.cssText = 'position:fixed;bottom:5rem;left:50%;transform:translateX(-50%);background:#111;border:1px solid rgba(255,255,255,0.15);color:white;padding:0.9rem 1.8rem;border-radius:4px;z-index:99999;font-size:0.9rem;transition:opacity 0.4s ease;';
        document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = '1';
    clearTimeout(t._timer);
    t._timer = setTimeout(() => { t.style.opacity = '0'; }, 2500);
}

// ─────────────────────────────────────────────────────────────
// 8. LEGAL PAGE VIEWS
// ─────────────────────────────────────────────────────────────
function showGallery() {
    document.getElementById('main-gallery').classList.remove('hidden');
    document.getElementById('vpg-hero').classList.remove('hidden');
    document.getElementById('vpg-search').classList.remove('hidden');
    document.getElementById('main-legal').classList.add('hidden');
    window.scrollTo(0, 0);
    document.title = 'Video Prompts Gallery — Cinematic AI Prompt Collection';

    // Clean up the URL bar (remove ?tab= param)
    history.pushState({}, '', '/');

    // Self-referencing canonical
    _setCanonical('https://video-prompts-gallery.onrender.com/');
}

function showLegal(page) {
    const p = page.toLowerCase();
    const content = LEGAL_CONTENT[p];
    if (!content) return;

    document.getElementById('main-gallery').classList.add('hidden');
    document.getElementById('vpg-hero').classList.add('hidden');
    document.getElementById('vpg-search').classList.add('hidden');
    document.getElementById('main-legal').classList.remove('hidden');

    const area = document.getElementById('legal-content-area');
    area.innerHTML = `<h2 style="font-family:'Playfair Display',serif;font-size:2.5rem;margin-bottom:2rem;">${content.title}</h2><div>${content.content}</div>`;
    window.scrollTo(0, 0);
    document.title = `${content.title} — Video Prompts Gallery`;

    // Update URL bar so the page is shareable
    history.pushState({}, '', `/?tab=${p}`);

    // Self-referencing canonical for the tab section
    _setCanonical(`https://video-prompts-gallery.onrender.com/?tab=${p}`);
}

/** Update or create the <link rel="canonical"> tag */
function _setCanonical(url) {
    // Guard: document.head is null inside Google Sites sandboxed iframes
    if (!document.head) return;
    let link = document.querySelector('link[rel="canonical"]');
    if (!link) {
        link = document.createElement('link');
        link.rel = 'canonical';
        document.head.appendChild(link);
    }
    link.href = url;
}

// ─────────────────────────────────────────────────────────────
// 9. ROUTING — share page & URL handling
// ─────────────────────────────────────────────────────────────
function handleRouting() {
    const params = new URLSearchParams(window.location.search);
    const promptId = params.get('prompt_id');
    const tab = (params.get('tab') || '').toLowerCase();

    if (promptId) {
        // Try immediately; if prompts not yet loaded this won't find it (shouldn't happen)
        const found = appState.prompts.find(p => p[F_ID] == promptId);
        if (found) {
            showDetail(promptId);
        } else {
            console.warn('prompt_id not found in data:', promptId);
        }
    } else if (tab && LEGAL_CONTENT[tab]) {
        // Handle direct links like /?tab=faq — show the correct legal/info page
        showLegal(tab);
    }

    // Cookie consent
    const cookieEl = document.getElementById('vpg-cookie-consent');
    if (cookieEl) {
        try {
            if (!localStorage.getItem('vpg_cookies_accepted')) {
                cookieEl.classList.remove('hidden');
            }
        } catch (e) {
            console.warn("localStorage blocked:", e);
        }
    }
}

// ─────────────────────────────────────────────────────────────
// 10. COOKIE CONSENT & UTILS
// ─────────────────────────────────────────────────────────────
function acceptCookies() {
    try {
        localStorage.setItem('vpg_cookies_accepted', '1');
    } catch (e) {}
    const el = document.getElementById('vpg-cookie-consent');
    if (el) el.classList.add('hidden');
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────
function initializeVPG() {
    initPreloader();
    fetchData();
    checkAdminSession();
    loadFeatureFlags();

    window.addEventListener('scroll', () => {
        const btt = document.getElementById('vpg-back-to-top');
        if (btt) btt.classList.toggle('visible', window.scrollY > 500);
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeVPG);
} else {
    initializeVPG();
}


// ═════════════════════════════════════════════════════════════
// ADMIN MODULE
// ═════════════════════════════════════════════════════════════

let adminState = { isAdmin: false };

// ═════════════════════════════════════════════════════════════
// FEATURE FLAGS MODULE
// ═════════════════════════════════════════════════════════════

let featureFlags = {};

// Human-readable labels for each flag
const FEATURE_FLAG_LABELS = {
    generate_button: 'Generate AI Image Button',
};

/**
 * Load feature flags from the public API and apply them to the UI.
 * Called on every page load for all visitors.
 */
async function loadFeatureFlags() {
    try {
        const res = await fetch(API_BASE + '/api/v1/feature-flags');
        if (!res.ok) {
            // Fetch failed — apply defaults (keep features enabled)
            applyFeatureFlags(Object.fromEntries(
                Object.keys(FEATURE_FLAG_LABELS).map(k => [k, true])
            ));
            return;
        }
        const flags = await res.json();
        featureFlags = flags;
        applyFeatureFlags(flags);
    } catch (e) {
        // Network error — apply defaults so UI is not broken
        applyFeatureFlags(Object.fromEntries(
            Object.keys(FEATURE_FLAG_LABELS).map(k => [k, true])
        ));
    }
}

/**
 * Show/hide UI elements based on the current flags.
 * Called both on initial load and after admin saves changes.
 */
function applyFeatureFlags(flags) {
    const enabled = !!flags.generate_button;

    // Generate AI Image floating button
    const genFab = document.getElementById('vpg-gen-fab-wrap');
    if (genFab) {
        genFab.classList.toggle('hidden', !enabled);
    }

    // Hide/show any Generate buttons already rendered in cards or modals
    document.querySelectorAll('.btn-generate-new').forEach(btn => {
        btn.style.display = enabled ? '' : 'none';
    });
}

// ─────────────────────────────────────────────────────────────
// Flipper Panel (admin-only UI)
// ─────────────────────────────────────────────────────────────

function toggleFlipperPanel() {
    const panel = document.getElementById('vpg-flipper-panel');
    if (!panel) return;
    const isHidden = panel.classList.toggle('hidden');
    if (!isHidden) {
        loadFlipperPanel();
    }
}

/**
 * Load full flag details from the admin endpoint and render checkboxes.
 */
async function loadFlipperPanel() {
    const list = document.getElementById('flipper-flags-list');
    const status = document.getElementById('flipper-save-status');
    if (!list) return;
    list.innerHTML = '<span class="flipper-loading">Loading…</span>';
    if (status) status.textContent = '';
    try {
        const res = await fetch(API_BASE + '/api/v1/admin/feature-flags');
        if (!res.ok) { list.innerHTML = '<span class="flipper-error">Failed to load flags.</span>'; return; }
        const flags = await res.json();
        featureFlags = Object.fromEntries(Object.entries(flags).map(([k, v]) => [k, v.enabled]));
        list.innerHTML = '';
        for (const [name, meta] of Object.entries(flags)) {
            const label = FEATURE_FLAG_LABELS[name] || name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            const row = document.createElement('label');
            row.className = 'flipper-flag-row';
            row.innerHTML = `
                <input type="checkbox" class="flipper-checkbox" id="flipper-${name}" data-flag="${name}" ${meta.enabled ? 'checked' : ''}>
                <span class="flipper-flag-label">${label}</span>
                <span class="flipper-flag-desc">${meta.description || ''}</span>
            `;
            list.appendChild(row);
        }
    } catch (e) {
        list.innerHTML = '<span class="flipper-error">Could not load feature flags.</span>';
    }
}

/**
 * Save all checkbox states to the server and immediately apply changes.
 */
async function saveFlipperSettings() {
    const btn = document.getElementById('flipper-save-btn');
    const status = document.getElementById('flipper-save-status');
    const checkboxes = document.querySelectorAll('.flipper-checkbox[data-flag]');
    if (!checkboxes.length) return;

    const payload = {};
    checkboxes.forEach(cb => { payload[cb.dataset.flag] = cb.checked; });

    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
    if (status) status.textContent = '';

    try {
        const res = await fetch(API_BASE + '/api/v1/admin/feature-flags', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            // Apply new flags immediately to the live page
            applyFeatureFlags(payload);
            featureFlags = { ...featureFlags, ...payload };
            if (status) { status.textContent = '✓ Saved & applied!'; status.className = 'flipper-save-status flipper-save-ok'; }
            showToast('🚦 Feature flags updated');
        } else {
            if (status) { status.textContent = data.message || 'Save failed.'; status.className = 'flipper-save-status flipper-save-err'; }
        }
    } catch (e) {
        if (status) { status.textContent = 'Network error — changes not saved.'; status.className = 'flipper-save-status flipper-save-err'; }
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '✔ Save & Apply'; }
    }
}

// ─────────────────────────────────────────────────────────────
// Session Check — runs on every page load
// ─────────────────────────────────────────────────────────────
async function checkAdminSession() {
    try {
        const res = await fetch(API_BASE + '/api/v1/admin/status');
        const data = await res.json();
        if (data.is_admin) {
            setAdminMode(true);
        }
    } catch (e) { /* not critical */ }
}

function setAdminMode(isAdmin) {
    adminState.isAdmin = isAdmin;
    const bar = document.getElementById('vpg-admin-bar');
    if (bar) bar.classList.toggle('hidden', !isAdmin);

    // Hide flipper panel when logging out
    if (!isAdmin) {
        const panel = document.getElementById('vpg-flipper-panel');
        if (panel) panel.classList.add('hidden');
    }

    // Shift navbar down when admin bar is showing
    document.documentElement.classList.toggle('admin-bar-active', isAdmin);

    // Re-render the grid so Edit buttons are shown/hidden
    if (appState.prompts.length) {
        renderGrid();
    }
}

// ─────────────────────────────────────────────────────────────
// Login Modal
// ─────────────────────────────────────────────────────────────
function openAdminLogin() {
    if (adminState.isAdmin) return; // Already logged in
    const modal = document.getElementById('vpg-admin-login-modal');
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        const input = document.getElementById('admin-password-input');
        if (input) { input.value = ''; setTimeout(() => input.focus(), 100); }
        const err = document.getElementById('admin-login-error');
        if (err) err.classList.add('hidden');
    }
}

function closeAdminLogin() {
    const modal = document.getElementById('vpg-admin-login-modal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
}

async function _sha256Hex(text) {
    const encoder = new TextEncoder();
    const data = encoder.encode(text);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function submitAdminLogin() {
    const input = document.getElementById('admin-password-input');
    const errEl = document.getElementById('admin-login-error');
    const password = (input ? input.value : '').trim();

    if (!password) {
        showAdminError(errEl, 'Please enter your password.');
        return;
    }

    try {
        // Hash the password client-side — raw password never leaves the browser
        const passwordHash = await _sha256Hex(password);
        const res = await fetch(API_BASE + '/api/v1/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: passwordHash })
        });
        const data = await res.json();

        if (res.ok && data.status === 'success') {
            closeAdminLogin();
            setAdminMode(true);
            showToast('🔐 Admin mode activated');
        } else {
            showAdminError(errEl, data.message || 'Invalid password. Please try again.');
            if (input) { input.value = ''; input.focus(); }
        }
    } catch (e) {
        showAdminError(errEl, 'Connection error. Please try again.');
    }
}

async function adminLogout() {
    try {
        await fetch(API_BASE + '/api/v1/admin/logout', { method: 'POST' });
    } catch (e) { }
    setAdminMode(false);
    showToast('Logged out of admin mode');
}

function showAdminError(el, msg) {
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('hidden');
}

// ─────────────────────────────────────────────────────────────
// Prompt Editor (Create / Edit)
// ─────────────────────────────────────────────────────────────
function openCreatePrompt() {
    if (!adminState.isAdmin) return;
    resetEditor();
    document.getElementById('editor-title').textContent = '+ Create New Prompt';
    document.getElementById('editor-prompt-id').value = '';
    openEditor();
}

function openEditPrompt(id) {
    if (!adminState.isAdmin) return;
    const prompt = appState.prompts.find(p => p[F_ID] == id);
    if (!prompt) return;

    resetEditor();
    document.getElementById('editor-title').textContent = '✏️ Edit Prompt';
    document.getElementById('editor-prompt-id').value = id;
    document.getElementById('editor-name').value = prompt[F_TITLE] || '';
    document.getElementById('editor-category').value = prompt[F_CATEGORY] || '';
    document.getElementById('editor-prompt').value = prompt[F_PROMPT] || '';
    document.getElementById('editor-video-id').value = prompt['Video ID'] || '';
    
    // Set AI Tool drop-down or default to Gemini
    const aiToolStr = (prompt['AI Tool'] || '').toLowerCase();
    const toolSelect = document.getElementById('editor-ai-tool');
    if (toolSelect) {
        toolSelect.value = aiToolStr;
    }

    if (document.getElementById('editor-image-url')) {
        document.getElementById('editor-image-url').value = prompt['Image URL'] || '';
    }
    openEditor();
}

function openEditor() {
    const editor = document.getElementById('vpg-prompt-editor');
    if (editor) {
        editor.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        setTimeout(() => document.getElementById('editor-name').focus(), 100);
    }
}

function closePromptEditor() {
    const editor = document.getElementById('vpg-prompt-editor');
    if (editor) editor.classList.add('hidden');
    document.body.style.overflow = '';
}

function resetEditor() {
    ['editor-name', 'editor-category', 'editor-video-id', 'editor-image-url', 'editor-image-file'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const ta = document.getElementById('editor-prompt');
    if (ta) ta.value = '';
    const err = document.getElementById('editor-error');
    if (err) err.classList.add('hidden');
    const btn = document.getElementById('editor-save-btn');
    if (btn) { btn.disabled = false; btn.textContent = '💾 Save Prompt'; }
}

async function savePrompt() {
    if (!adminState.isAdmin) return;

    const promptId = (document.getElementById('editor-prompt-id').value || '').trim();
    const name = (document.getElementById('editor-name').value || '').trim();
    const category = (document.getElementById('editor-category').value || '').trim();
    const prompt = (document.getElementById('editor-prompt').value || '').trim();
    const videoId = (document.getElementById('editor-video-id').value || '').trim();
    const aiToolSelect = document.getElementById('editor-ai-tool');
    const aiTool = aiToolSelect ? aiToolSelect.value : '';
    const btnUrlEl = document.getElementById('editor-image-url');
    let imageUrl = btnUrlEl ? btnUrlEl.value.trim() : '';
    const errEl = document.getElementById('editor-error');
    const saveBtn = document.getElementById('editor-save-btn');
    const fileInput = document.getElementById('editor-image-file');

    if (!name || !prompt) {
        showAdminError(errEl, 'Prompt Name and Prompt Text are required.');
        return;
    }

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';

    try {
        if (fileInput && fileInput.files.length > 0) {
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);

            saveBtn.textContent = 'Uploading image...';
            let uploadRes, uploadData;
            try {
                uploadRes = await fetch(API_BASE + '/api/v1/admin/upload-image', {
                    method: 'POST',
                    body: formData
                });
                uploadData = await uploadRes.json();
            } catch (uploadNetErr) {
                showAdminError(errEl, '❌ Upload failed: Could not reach server. Check your internet connection.');
                saveBtn.disabled = false;
                saveBtn.textContent = '💾 Save Prompt';
                return;
            }

            if (uploadData.status === 'success') {
                imageUrl = uploadData.url;
            } else {
                showAdminError(errEl, `❌ Upload failed: ${uploadData.message || 'Unknown error from server.'}`);
                saveBtn.disabled = false;
                saveBtn.textContent = '💾 Save Prompt';
                return;
            }
        }

        saveBtn.textContent = 'Saving Prompt...';

        const isEdit = Boolean(promptId);
        const url = isEdit
            ? `${API_BASE}/api/v1/admin/prompt/${encodeURIComponent(promptId)}`
            : API_BASE + '/api/v1/admin/prompt';
        const method = isEdit ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, category, prompt, video_id: videoId, ai_tool: aiTool, image_url: imageUrl })
        });
        const data = await res.json();

        if (res.ok && data.status === 'success') {
            closePromptEditor();
            showToast(isEdit ? '✅ Prompt updated!' : '✅ New prompt created!');
            // Refresh data from server
            await refreshData();
        } else {
            showAdminError(errEl, data.message || 'Save failed. Try again.');
            saveBtn.disabled = false;
            saveBtn.textContent = '💾 Save Prompt';
        }
    } catch (e) {
        showAdminError(errEl, `Connection error: ${e.message || 'Please try again.'}`);
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save Prompt';
    }
}

// Force a fresh data pull (busts cache)
async function refreshData() {
    try {
        const response = await fetch(API_BASE + '/api/v1/prompts?_=' + Date.now());
        const data = await response.json();
        appState.prompts = data.prompts || [];
        appState.analytics = data.analytics || [];
        appState.comments = data.comments || [];
        renderFilters();
        renderGrid();
    } catch (e) {
        console.error('refreshData error', e);
    }
}


// ═════════════════════════════════════════════════════════════
// USER AUTH MODULE
// ═════════════════════════════════════════════════════════════

const authState = {
    loggedIn: false,
    userName: '',
    userEmail: '',
};

// Check auth status on page load
async function checkAuthStatus() {
    try {
        const res = await fetch(API_BASE + '/api/auth/status');
        const data = await res.json();
        if (data.logged_in) {
            authState.loggedIn = true;
            authState.userName = data.user.name;
            authState.userEmail = data.user.email;
        } else {
            authState.loggedIn = false;
            authState.userName = '';
            authState.userEmail = '';
        }
        _updateUserBadge();
    } catch (e) {
        console.error('Auth status check failed:', e);
    }
}

function _updateUserBadge() {
    const badge = document.getElementById('vpg-user-badge');
    const nameEl = document.getElementById('vpg-user-name');
    const avatarEl = document.getElementById('vpg-user-avatar');
    if (!badge) return;
    if (authState.loggedIn) {
        badge.classList.remove('hidden');
        if (nameEl) nameEl.textContent = authState.userName || authState.userEmail;
        if (avatarEl) avatarEl.textContent = (authState.userName || 'U')[0].toUpperCase();
    } else {
        badge.classList.add('hidden');
    }
}

function openAuthModal(tab) {
    const modal = document.getElementById('vpg-auth-modal');
    if (modal) modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    switchAuthTab(tab || 'login');
    _clearAuthMessage();
}

function closeAuthModal() {
    const modal = document.getElementById('vpg-auth-modal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function switchAuthTab(tab) {
    const loginTab = document.getElementById('auth-tab-login');
    const regTab = document.getElementById('auth-tab-register');
    const loginForm = document.getElementById('auth-form-login');
    const regForm = document.getElementById('auth-form-register');
    _clearAuthMessage();
    if (tab === 'login') {
        loginTab?.classList.add('active');
        regTab?.classList.remove('active');
        loginForm?.classList.remove('hidden');
        regForm?.classList.add('hidden');
    } else {
        regTab?.classList.add('active');
        loginTab?.classList.remove('active');
        regForm?.classList.remove('hidden');
        loginForm?.classList.add('hidden');
    }
}

function _showAuthMessage(msg, isError) {
    const el = document.getElementById('auth-message');
    if (!el) return;
    el.textContent = msg;
    el.className = 'auth-message' + (isError ? ' auth-error' : ' auth-success');
    el.classList.remove('hidden');
}

function _clearAuthMessage() {
    const el = document.getElementById('auth-message');
    if (el) { el.classList.add('hidden'); el.textContent = ''; }
}

// Validation helpers
function _isValidEmail(email) {
    return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
}

function _isValidPassword(password) {
    return password && password.length >= 6;
}

function _isValidApiKey(key) {
    return key && key.trim().startsWith('AIza');
}

function _showFieldError(fieldId, message) {
    const errorEl = document.getElementById(fieldId + '-error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('show');
    }
}

function _clearFieldError(fieldId) {
    const errorEl = document.getElementById(fieldId + '-error');
    if (errorEl) {
        errorEl.textContent = '';
        errorEl.classList.remove('show');
    }
}

function _clearAllFieldErrors(prefix) {
    const fields = ['name', 'email', 'password', 'apikey'];
    fields.forEach(f => _clearFieldError(`auth-${prefix}-${f}`));
}

function togglePasswordVisibility(fieldId) {
    const input = document.getElementById(fieldId);
    const icon = document.getElementById(fieldId + '-icon');
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    if (icon) icon.textContent = isPassword ? '🙈' : '👁️';
}

async function submitLogin() {
    const emailEl = document.getElementById('auth-login-email');
    const passwordEl = document.getElementById('auth-login-password');
    const email = (emailEl?.value || '').trim();
    const password = passwordEl?.value || '';

    _clearAllFieldErrors('login');
    _clearAuthMessage();

    let hasError = false;
    if (!email) {
        _showFieldError('auth-login-email', 'Email is required');
        hasError = true;
    } else if (!_isValidEmail(email)) {
        _showFieldError('auth-login-email', 'Please enter a valid email address');
        hasError = true;
    }

    if (!password) {
        _showFieldError('auth-login-password', 'Password is required');
        hasError = true;
    }

    if (hasError) return;

    const btn = document.querySelector('#auth-form-login .auth-submit-btn');
    const lbl = document.getElementById('auth-login-label');
    if (btn) btn.disabled = true;
    if (lbl) lbl.textContent = 'Logging in…';

    try {
        const res = await fetch(API_BASE + '/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            authState.loggedIn = true;
            authState.userName = data.user.name;
            authState.userEmail = data.user.email;
            _updateUserBadge();
            closeAuthModal();
            if (_authPendingGenerate) {
                _authPendingGenerate = false;
                imggenGenerate();
            }
        } else {
            _showAuthMessage(data.message || 'Login failed.', true);
        }
    } catch (e) {
        _showAuthMessage('Network error. Please try again.', true);
    } finally {
        if (btn) btn.disabled = false;
        if (lbl) lbl.textContent = 'Login';
    }
}

async function submitRegister() {
    const name = (document.getElementById('auth-reg-name')?.value || '').trim();
    const email = (document.getElementById('auth-reg-email')?.value || '').trim();
    const password = document.getElementById('auth-reg-password')?.value || '';
    const apiKey = (document.getElementById('auth-reg-apikey')?.value || '').trim();

    _clearAllFieldErrors('reg');
    _clearAuthMessage();

    let hasError = false;
    if (!name || name.length < 2) {
        _showFieldError('auth-reg-name', 'Please enter your full name (at least 2 characters)');
        hasError = true;
    }

    if (!email) {
        _showFieldError('auth-reg-email', 'Email is required');
        hasError = true;
    } else if (!_isValidEmail(email)) {
        _showFieldError('auth-reg-email', 'Please enter a valid email address (e.g., user@example.com)');
        hasError = true;
    }

    if (!password) {
        _showFieldError('auth-reg-password', 'Password is required');
        hasError = true;
    } else if (!_isValidPassword(password)) {
        _showFieldError('auth-reg-password', 'Password must be at least 6 characters long');
        hasError = true;
    }

    if (!apiKey) {
        _showFieldError('auth-reg-apikey', 'Gemini API key is required');
        hasError = true;
    } else if (!_isValidApiKey(apiKey)) {
        _showFieldError('auth-reg-apikey', 'Invalid API key format. It must start with "AIza..." — get it from aistudio.google.com/apikey');
        hasError = true;
    }

    if (hasError) return;

    const btn = document.querySelector('#auth-form-register .auth-submit-btn');
    const lbl = document.getElementById('auth-reg-label');
    if (btn) btn.disabled = true;
    if (lbl) lbl.textContent = 'Creating account…';

    try {
        const res = await fetch(API_BASE + '/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password, api_key: apiKey }),
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            authState.loggedIn = true;
            authState.userName = data.user.name;
            authState.userEmail = data.user.email;
            _updateUserBadge();
            closeAuthModal();
            if (_authPendingGenerate) {
                _authPendingGenerate = false;
                imggenGenerate();
            }
        } else {
            _showAuthMessage(data.message || 'Registration failed.', true);
        }
    } catch (e) {
        _showAuthMessage('Network error. Please try again.', true);
    } finally {
        if (btn) btn.disabled = false;
        if (lbl) lbl.textContent = 'Create Account';
    }
}

async function userLogout() {
    try {
        await fetch(API_BASE + '/api/auth/logout', { method: 'POST' });
    } catch (e) { /* ignore */ }
    authState.loggedIn = false;
    authState.userName = '';
    authState.userEmail = '';
    _updateUserBadge();
}

// Flag: user tried to generate before logging in
let _authPendingGenerate = false;

function toggleApiKeyGuide() {
    const steps = document.getElementById('apikey-guide-steps');
    const arrow = document.getElementById('apikey-guide-arrow');
    if (!steps) return;
    const isHidden = steps.classList.toggle('hidden');
    if (arrow) arrow.textContent = isHidden ? '▼' : '▲';
}

// Call on page load
document.addEventListener('DOMContentLoaded', () => { checkAuthStatus(); });


// ═════════════════════════════════════════════════════════════
// AI IMAGE GENERATOR MODULE (UNIFIED VIEW)
// ═════════════════════════════════════════════════════════════

const imgGenState = {
    mode: 'list', // 'list' or 'manual'
    selectedListPrompt: '',
    referenceImageB64: '',
    referenceImageMime: '',
    generatedImageB64: '',
    generatedMime: 'image/png',
    retriesLeft: 3,
    isGenerating: false,
    aspectRatio: '1:1',
    _progressTimers: [],
};

// ── Open / Close ──────────────────────────────────────────────
function openImageGen(prefillPrompt = '', promptTitle = '') {
    // ── Auth check: user must be logged in to use image generator ──
    if (!authState.loggedIn && !(adminState && adminState.isAdmin)) {
        _authPendingGenerate = true;
        openAuthModal('login');
        return;
    }

    const modal = document.getElementById('vpg-imggen-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Reset retries every fresh open
    imgGenState.retriesLeft = 3;
    const countEl = document.getElementById('imggen-retry-count');
    if (countEl) countEl.textContent = 3;

    _imgGenPopulateDropdown();

    // Set textarea or dropdown based on prefill
    const ta = document.getElementById('imggen-custom-prompt');
    if (prefillPrompt && promptTitle) {
        // If coming from a specific card, switch to manual mode safely
        imgGenState.mode = 'manual';
        if (ta) ta.value = prefillPrompt;
        const manualRadio = document.querySelector('input[name="prompt_mode"][value="manual"]');
        if (manualRadio) manualRadio.checked = true;
    } else {
        // Default to list mode if opening generically via FAB
        imgGenState.mode = 'list';
        const listRadio = document.querySelector('input[name="prompt_mode"][value="list"]');
        if (listRadio) listRadio.checked = true;
        if (ta) ta.value = '';
    }

    togglePromptMode();
    _imgGenUpdateSummary(promptTitle);
    _imgGenHideResult();
    _imgGenHideError();
}

function closeImageGen() {
    const modal = document.getElementById('vpg-imggen-modal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Attach custom-prompt listener after DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const ta = document.getElementById('imggen-custom-prompt');
    if (ta) {
        ta.addEventListener('input', () => _imgGenUpdateSummary());
    }
});

// ── Radio Modes & Dropdown ────────────────────────────────────
function togglePromptMode() {
    const radios = document.getElementsByName('prompt_mode');
    radios.forEach(r => {
        if (r.checked) imgGenState.mode = r.value;
    });

    const modeList = document.getElementById('imggen-mode-list');
    const modeManual = document.getElementById('imggen-mode-manual');

    if (imgGenState.mode === 'list') {
        if (modeList) modeList.classList.remove('hidden');
        if (modeManual) modeManual.classList.add('hidden');
    } else {
        if (modeList) modeList.classList.add('hidden');
        if (modeManual) modeManual.classList.remove('hidden');
    }
    _imgGenUpdateSummary();
}

function _imgGenPopulateDropdown() {
    const select = document.getElementById('imggen-prompt-dropdown');
    if (!select) return;

    select.innerHTML = '<option value="">-- Choose a cinematic prompt --</option>';

    const prompts = appState.prompts || [];
    prompts.forEach(p => {
        const title = p[F_TITLE] || 'Untitled';
        const txt = p[F_PROMPT] || '';
        const opt = document.createElement('option');
        // store the prompt text as the value to easily extract
        opt.value = txt;
        opt.textContent = title;
        select.appendChild(opt);
    });

    select.value = '';
    imgGenState.selectedListPrompt = '';
    const preview = document.getElementById('imggen-selected-preview');
    if (preview) preview.textContent = '';
}

function selectDropdownPrompt() {
    const select = document.getElementById('imggen-prompt-dropdown');
    const preview = document.getElementById('imggen-selected-preview');
    if (!select || !preview) return;

    imgGenState.selectedListPrompt = select.value;

    if (select.value) {
        preview.textContent = select.value;
    } else {
        preview.textContent = '';
    }
    _imgGenUpdateSummary();
}

// ── Summary bar ───────────────────────────────────────────────
function _imgGenUpdateSummary(titleHint) {
    const el = document.getElementById('imggen-summary');
    if (!el) return;

    const hasRef = Boolean(imgGenState.referenceImageB64);
    let text = '';

    if (imgGenState.mode === 'list') {
        const select = document.getElementById('imggen-prompt-dropdown');
        if (select && select.value) {
            // grab the title from the selected option label
            const title = select.options[select.selectedIndex].text;
            text = `Prompt: ${title}`;
        } else {
            text = 'No prompt selected from list';
        }
    } else {
        const customTa = document.getElementById('imggen-custom-prompt');
        const customText = (customTa ? customTa.value : '').trim();
        if (customText) {
            text = titleHint ? `Prompt: ${titleHint}` : `Prompt: "${customText.slice(0, 40)}${customText.length > 40 ? '\u2026' : ''}"`;
        } else {
            text = 'No prompt written yet';
        }
    }

    if (text === 'No prompt selected from list' || text === 'No prompt written yet') {
        el.textContent = text;
        return;
    }

    const ratioSel = document.getElementById('imggen-aspect-ratio');
    const ratio = ratioSel ? ratioSel.value : '1:1';
    el.textContent = text + (hasRef ? '  \u00b7  \uD83D\uDCCE Image attached' : '') + '  \u00b7  ' + ratio;
}

// ── Image Upload ──────────────────────────────────────────────
function imggenFileSelected(evt) {
    const file = evt.target.files && evt.target.files[0];
    _imgGenLoadFile(file);
}

function imggenDragOver(evt) {
    evt.preventDefault();
    const z = document.getElementById('imggen-upload-zone');
    if (z) z.classList.add('drag-over');
}

function imggenDragLeave() {
    const z = document.getElementById('imggen-upload-zone');
    if (z) z.classList.remove('drag-over');
}

function imggenDrop(evt) {
    evt.preventDefault();
    const z = document.getElementById('imggen-upload-zone');
    if (z) z.classList.remove('drag-over');
    const file = evt.dataTransfer.files && evt.dataTransfer.files[0];
    _imgGenLoadFile(file);
}

function _imgGenLoadFile(file) {
    if (!file) return;
    _imgGenHideError();
    if (!file.type.startsWith('image/')) {
        _imgGenShowError('Please upload an image file (JPG, PNG, WEBP, GIF).');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        _imgGenShowError('Image too large. Maximum allowed size is 10 MB.');
        return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
        const dataUrl = e.target.result;
        imgGenState.referenceImageB64 = dataUrl;
        imgGenState.referenceImageMime = file.type;

        const wrap = document.getElementById('imggen-preview-wrap');
        const img = document.getElementById('imggen-preview-img');
        const zone = document.getElementById('imggen-upload-zone');
        if (img) img.src = dataUrl;
        if (wrap) wrap.classList.remove('hidden');
        if (zone) zone.classList.add('hidden'); // Hide dropzone completely
        _imgGenUpdateSummary();
    };
    reader.readAsDataURL(file);
}

function imggenRemoveImage() {
    imgGenState.referenceImageB64 = '';
    imgGenState.referenceImageMime = '';
    const wrap = document.getElementById('imggen-preview-wrap');
    const img = document.getElementById('imggen-preview-img');
    const zone = document.getElementById('imggen-upload-zone');
    const input = document.getElementById('imggen-file-input');
    if (img) img.src = '';
    if (wrap) wrap.classList.add('hidden');
    if (zone) zone.classList.remove('hidden'); // Restore dropzone

    if (input) input.value = '';
    _imgGenUpdateSummary();
}

// ── Generate ──────────────────────────────────────────────────
async function imggenGenerate() {
    if (imgGenState.isGenerating) return;

    let promptText = '';
    if (imgGenState.mode === 'list') {
        promptText = imgGenState.selectedListPrompt;
        if (!promptText) {
            _imgGenShowError('Please select a prompt from the list.');
            return;
        }
    } else {
        const customTa = document.getElementById('imggen-custom-prompt');
        promptText = (customTa ? customTa.value : '').trim();
        if (!promptText) {
            _imgGenShowError('Please manually enter a prompt.');
            return;
        }
    }

    const ratioEl = document.getElementById('imggen-aspect-ratio');
    imgGenState.aspectRatio = ratioEl ? ratioEl.value : '1:1';
    imgGenState.isGenerating = true;
    imgGenState.retriesLeft = 3;
    _imgGenSetLoading(true, 'Generating image\u2026');
    _imgGenHideError();
    _imgGenHideResult();
    _imgGenStartProgress();
    await _imgGenCallAPI(promptText);
}

// ── Retry ──────────────────────────────────────────────────────
async function imggenRetry() {
    if (imgGenState.isGenerating || imgGenState.retriesLeft <= 0) return;

    let promptText = '';
    if (imgGenState.mode === 'list') {
        promptText = imgGenState.selectedListPrompt;
    } else {
        const customTa = document.getElementById('imggen-custom-prompt');
        promptText = (customTa ? customTa.value : '').trim();
    }

    const ratioEl = document.getElementById('imggen-aspect-ratio');
    imgGenState.aspectRatio = ratioEl ? ratioEl.value : '1:1';
    imgGenState.isGenerating = true;
    imgGenState.retriesLeft -= 1;
    _imgGenSetLoading(true, 'Regenerating\u2026');
    _imgGenHideError();
    _imgGenHideResult();
    _imgGenStartProgress();
    // Always sends the ORIGINAL reference image on every retry
    await _imgGenCallAPI(promptText);
}

// ── API call ──────────────────────────────────────────────────
async function _imgGenCallAPI(promptText) {
    try {
        const res = await fetch(API_BASE + '/api/v1/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: promptText,
                image_b64: imgGenState.referenceImageB64 || '',
                mime_type: imgGenState.referenceImageMime || 'image/jpeg',
                aspect_ratio: imgGenState.aspectRatio || '1:1',
            }),
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
            imgGenState.generatedImageB64 = data.image_b64;
            imgGenState.generatedMime = data.mime_type || 'image/png';
            _imgGenShowResult(data.image_b64);
        } else if (res.status === 401 && data.message === 'LOGIN_REQUIRED') {
            // Session expired — prompt re-login
            authState.loggedIn = false;
            _updateUserBadge();
            _authPendingGenerate = true;
            openAuthModal('login');
            _imgGenShowError('Your session has expired. Please log in again.');
        } else {
            _imgGenShowError(data.message || 'Generation failed. Please try again.');
        }
    } catch (err) {
        _imgGenShowError('Network error. Please check your connection and try again.');
    } finally {
        imgGenState.isGenerating = false;
        _imgGenSetLoading(false, 'Generate Image');
        _imgGenStopProgress();
        const countEl = document.getElementById('imggen-retry-count');
        const retryBtn = document.getElementById('imggen-retry-btn');
        if (countEl) countEl.textContent = imgGenState.retriesLeft;
        if (retryBtn) retryBtn.disabled = imgGenState.retriesLeft <= 0;
    }
}

// ── Download ──────────────────────────────────────────────────
function imggenDownload() {
    const src = imgGenState.generatedImageB64;
    if (!src) return;
    const ext = (imgGenState.generatedMime || 'image/png').split('/')[1] || 'png';
    const link = document.createElement('a');
    link.href = src;
    link.download = `vpg-ai-${Date.now()}.${ext}`;
    link.click();
}

// ── Minimize / Close result panel ────────────────────────────
function imggenToggleMinimize() {
    const result = document.getElementById('imggen-result');
    const btn = document.getElementById('imggen-minimize-btn');
    if (!result) return;
    const isMin = result.classList.toggle('minimized');
    if (btn) btn.textContent = isMin ? '\u25bc Expand' : '\u25b2 Minimize';
    if (!isMin) {
        result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function imggenCloseResult() {
    const result = document.getElementById('imggen-result');
    if (result) {
        result.classList.add('hidden');
        result.classList.remove('minimized');
    }
    const btn = document.getElementById('imggen-minimize-btn');
    if (btn) btn.textContent = '\u25b2 Minimize';
    imgGenState.generatedImageB64 = '';
    imgGenState.generatedMime = 'image/png';
}

// ── UI helpers ────────────────────────────────────────────────
function _imgGenSetLoading(loading, label) {
    const btn = document.getElementById('imggen-generate-btn');
    const lbl = document.getElementById('imggen-btn-label');
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle('loading', loading);
    if (lbl) lbl.textContent = loading ? label : 'Generate Image';
}

function _imgGenShowResult(dataUrl) {
    const result = document.getElementById('imggen-result');
    const img = document.getElementById('imggen-result-img');
    if (img) img.src = dataUrl;
    if (result) {
        result.classList.remove('hidden');
        result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function _imgGenHideResult() {
    const result = document.getElementById('imggen-result');
    if (result) result.classList.add('hidden');
}

function _imgGenShowError(rawMsg) {
    const el = document.getElementById('imggen-error');
    const icon = document.getElementById('imggen-error-icon');
    const title = document.getElementById('imggen-error-title');
    const msg = document.getElementById('imggen-error-msg');
    const tip = document.getElementById('imggen-error-tip');
    if (!el) return;

    // Map raw technical errors to friendly messages
    const r = (rawMsg || '').toLowerCase();
    let friendly = { icon: '\u26a0\ufe0f', titleText: 'Generation failed', msgText: '', tipText: '', warn: false };

    if (r.includes('429') || r.includes('quota') || r.includes('exceeded')) {
        friendly = {
            icon: '\u23f3',
            titleText: 'AI quota limit reached',
            msgText: 'All AI providers have hit their free-tier usage limit for today.',
            tipText: 'This resets automatically. Try again in a few minutes or later today.',
            warn: true
        };
    } else if (r.includes('billing') || r.includes('billing_hard_limit') || r.includes('billing_not_enabled') || r.includes('failed_precondition')) {
        friendly = {
            icon: '\uD83D\uDCB3',
            titleText: 'Cloud Billing not enabled',
            msgText: 'Your Gemini API key works for text, but image generation requires Cloud Billing to be enabled on your Google Cloud project.',
            tipText: 'Go to console.cloud.google.com → Billing → Link a billing account to your project. Image generation is still free within quota limits once billing is enabled.',
            warn: true
        };
    } else if (r.includes('network') || r.includes('connection')) {
        friendly = {
            icon: '\uD83D\uDCF6',
            titleText: 'Connection problem',
            msgText: 'Could not reach the AI service. Check your internet connection.',
            tipText: 'Try refreshing the page or waiting a moment before retrying.',
            warn: false
        };
    } else if (r.includes('no api key') || r.includes('not configured')) {
        friendly = {
            icon: '\uD83D\uDD11',
            titleText: 'API key not configured',
            msgText: 'No AI provider API keys are set up on this server.',
            tipText: 'Contact the site admin to configure Gemini or OpenAI keys.',
            warn: false
        };
    } else if (r.includes('prompt is required')) {
        friendly = {
            icon: '\u270F\uFE0F',
            titleText: 'Prompt required',
            msgText: 'Please write or select a prompt before generating.',
            tipText: '',
            warn: true
        };
    } else {
        friendly = {
            icon: '\u26A0\uFE0F',
            titleText: 'Image generation failed',
            msgText: 'Something went wrong. Please try again or change your prompt.',
            tipText: 'If this keeps happening, the AI service may be temporarily unavailable.',
            warn: false
        };
    }

    if (icon) icon.textContent = friendly.icon;
    if (title) title.textContent = friendly.titleText;
    if (msg) msg.textContent = friendly.msgText;
    if (tip) tip.textContent = friendly.tipText;
    el.classList.toggle('warn', friendly.warn);
    el.classList.remove('hidden');
}

function _imgGenHideError() {
    const el = document.getElementById('imggen-error');
    if (el) { el.classList.add('hidden'); el.classList.remove('warn'); }
}

// ── Progress indicator ────────────────────────────────────────
const _PROGRESS_STEPS = [
    { delay: 0, pct: 8, label: '\u25b6 Sending to Gemini AI (image-editing mode)…' },
    { delay: 15000, pct: 40, label: '\u25b6 Gemini is rendering your image…' },
    { delay: 50000, pct: 65, label: '\u25b6 Trying next Gemini model…' },
    { delay: 80000, pct: 85, label: '\u25b6 Falling back to OpenAI DALL·E 3…' },
    { delay: 110000, pct: 95, label: '\u25b6 Almost there…' },
];

function _imgGenStartProgress() {
    const el = document.getElementById('imggen-progress');
    const lbl = document.getElementById('imggen-progress-label');
    const fill = document.getElementById('imggen-progress-fill');
    if (!el) return;
    el.classList.remove('hidden');
    if (fill) { fill.style.transition = 'none'; fill.style.width = '0%'; }
    if (lbl) lbl.textContent = '';
    imgGenState._progressTimers = _PROGRESS_STEPS.map(({ delay, pct, label }) =>
        setTimeout(() => {
            if (lbl) lbl.textContent = label;
            if (fill) { fill.style.transition = 'width 3s ease'; fill.style.width = pct + '%'; }
        }, delay)
    );
}

function _imgGenStopProgress() {
    (imgGenState._progressTimers || []).forEach(t => clearTimeout(t));
    imgGenState._progressTimers = [];
    const el = document.getElementById('imggen-progress');
    if (el) el.classList.add('hidden');
}


// ─────────────────────────────────────────────────────────────
// PWA CUSTOM INSTALL LOGIC
// ─────────────────────────────────────────────────────────────
let deferredPrompt;
const pwaPopup = document.getElementById('vpg-pwa-popup');
const pwaInstallBtn = document.getElementById('vpg-pwa-install-btn');
const iosInstructions = document.getElementById('vpg-pwa-ios-instructions');

// Check if user already dismissed or installed
const hasDismissedPwa = localStorage.getItem('vpg_pwa_dismissed');

// Listen for Android/Desktop install event
window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the default mini-infobar
    e.preventDefault();
    deferredPrompt = e;
    
    // Show our custom popup if not dismissed
    if (!hasDismissedPwa && pwaPopup) {
        setTimeout(() => pwaPopup.classList.add('show'), 3000); // show after 3 seconds
    }
});

function installPwa() {
    if (deferredPrompt) {
        // Show the native browser prompt
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('User accepted the install prompt');
            }
            deferredPrompt = null;
            dismissPwaPopup();
        });
    }
}

function dismissPwaPopup() {
    if (pwaPopup) {
        pwaPopup.classList.remove('show');
        localStorage.setItem('vpg_pwa_dismissed', 'true');
    }
}

// iOS Safari special handling
const isIos = () => {
    const userAgent = window.navigator.userAgent.toLowerCase();
    return /iphone|ipad|ipod/.test(userAgent);
};

// Detect if running in standalone mode (already installed)
const isInStandaloneMode = () => ('standalone' in window.navigator) && (window.navigator.standalone);

window.addEventListener('load', () => {
    // If it's an iPhone in Safari, and NOT already installed as an app, and not dismissed
    if (isIos() && !isInStandaloneMode() && !hasDismissedPwa && pwaPopup) {
        // Hide the install button because iOS doesn't support programmatic install
        if(pwaInstallBtn) pwaInstallBtn.style.display = 'none';
        // Show instructions text instead
        if(iosInstructions) iosInstructions.classList.remove('hidden');
        
        setTimeout(() => pwaPopup.classList.add('show'), 3000);
    }
});
