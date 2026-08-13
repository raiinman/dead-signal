<?php
declare(strict_types=1);

const DS_X_HANDLE = 'OnceHuman_';
const DS_X_NAME = 'Once Human';
const DS_X_CACHE_TTL = 300;
const DS_X_MAX_ITEMS = 8;
const DS_X_CACHE_VERSION = 6;
const DS_BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36';

$cacheFile = __DIR__ . '/timeline-cache.json';
$lockFile = __DIR__ . '/timeline-cache.lock';
$profileUrl = 'https://x.com/' . DS_X_HANDLE;

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: public, max-age=60, stale-while-revalidate=600');
header('X-Content-Type-Options: nosniff');

function ds_read_cache(string $file): ?array {
    if (!is_file($file)) return null;
    $raw = @file_get_contents($file);
    if ($raw === false || $raw === '') return null;
    $data = json_decode($raw, true);
    return is_array($data) ? $data : null;
}

function ds_write_cache(string $file, array $data): void {
    $tmp = $file . '.tmp';
    $json = json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    if ($json === false) return;
    if (@file_put_contents($tmp, $json . "\n", LOCK_EX) !== false) {
        @rename($tmp, $file);
    }
}

function ds_http_get(string $url, array $headers = [], int $timeout = 30, ?string $userAgent = null): ?array {
    if (!function_exists('curl_init')) return null;

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_TIMEOUT => $timeout,
        CURLOPT_ENCODING => '',
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_USERAGENT => $userAgent ?: 'DeadSignal/1.0 (+https://deadsignaldb.com/)',
    ]);

    $body = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);

    if (!is_string($body) || $body === '' || $status < 200 || $status >= 300) return null;
    return ['status' => $status, 'body' => $body];
}

function ds_fetch_public_x_html(string $url, int $timeout = 35): ?string {
    $response = ds_http_get($url, [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language: en-US,en;q=0.9',
        'Cache-Control: no-cache',
        'Pragma: no-cache',
        'Sec-Fetch-Dest: document',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-Site: none',
        'Upgrade-Insecure-Requests: 1',
    ], $timeout, DS_BROWSER_UA);

    if (!$response) return null;
    return (string)$response['body'];
}

function ds_normalize_x_html(string $content): string {
    $content = html_entity_decode($content, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    return str_replace(
        ['\\/', '\\u002F', '\\u002f', '\\u003A', '\\u003a', '\\u0026', '\\u003D', '\\u003d', '\\u003F', '\\u003f'],
        ['/', '/', '/', ':', ':', '&', '=', '=', '?', '?'],
        $content
    );
}

function ds_extract_profile_avatar(string $content): string {
    $content = ds_normalize_x_html($content);
    if (preg_match('~https://pbs\.twimg\.com/profile_images/[^\s)\]"\']+~i', $content, $m)) {
        return $m[0];
    }
    return '';
}

function ds_extract_statuses(string $content): array {
    $content = ds_normalize_x_html($content);
    $quotedHandle = preg_quote(DS_X_HANDLE, '~');
    $pattern = '~(?:(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com))?/' . $quotedHandle . '/status/(\d+)~i';

    $found = [];
    if (preg_match_all($pattern, $content, $matches, PREG_SET_ORDER)) {
        foreach ($matches as $match) {
            $id = (string)($match[1] ?? '');
            if ($id === '' || !ctype_digit($id)) continue;
            $found[$id] = 'https://x.com/' . DS_X_HANDLE . '/status/' . $id;
        }
    }

    uksort($found, static function (string $a, string $b): int {
        if (strlen($a) !== strlen($b)) return strlen($b) <=> strlen($a);
        return strcmp($b, $a);
    });

    return array_slice($found, 0, DS_X_MAX_ITEMS, true);
}

function ds_snowflake_time(string $id): string {
    if (!ctype_digit($id) || PHP_INT_SIZE < 8) return '';
    $value = (int)$id;
    $milliseconds = ($value >> 22) + 1288834974657;
    if ($milliseconds <= 0) return '';
    return gmdate('c', intdiv($milliseconds, 1000));
}

function ds_safe_post_html(string $html): string {
    if (!class_exists('DOMDocument')) return h(strip_tags($html));

    $dom = new DOMDocument();
    $previous = libxml_use_internal_errors(true);
    $dom->loadHTML('<?xml encoding="utf-8" ?>' . $html, LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD);
    libxml_clear_errors();
    libxml_use_internal_errors($previous);

    $paragraph = $dom->getElementsByTagName('p')->item(0);
    if (!$paragraph) return '';

    $renderNode = function (DOMNode $node) use (&$renderNode): string {
        if ($node instanceof DOMText) return h($node->nodeValue ?? '');
        if (!($node instanceof DOMElement)) return '';

        $tag = strtolower($node->tagName);
        $inner = '';
        foreach ($node->childNodes as $child) $inner .= $renderNode($child);

        if ($tag === 'br') return '<br>';
        if ($tag !== 'a') return $inner;

        $href = trim($node->getAttribute('href'));
        if (!preg_match('~^https?://~i', $href)) return $inner;
        return '<a href="' . h($href) . '" target="_blank" rel="noopener noreferrer">' . $inner . '</a>';
    };

    $out = '';
    foreach ($paragraph->childNodes as $child) $out .= $renderNode($child);
    return trim($out);
}

// X's public oEmbed endpoint is keyless. No developer account, bearer token,
// API key, OAuth flow, or visitor-side X JavaScript is used by Dead Signal.
function ds_fetch_oembed(string $url): ?array {
    $query = http_build_query([
        'url' => $url,
        'omit_script' => 1,
        'dnt' => 'true',
        'theme' => 'dark',
    ], '', '&', PHP_QUERY_RFC3986);

    $response = ds_http_get('https://publish.x.com/oembed?' . $query, [
        'Accept: application/json',
    ], 20);
    if (!$response) return null;

    $data = json_decode((string)$response['body'], true);
    return is_array($data) ? $data : null;
}

function ds_media_candidate(string $url): string {
    $url = html_entity_decode(trim($url), ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $url = rtrim($url, "\\\"'.,;)]}");
    if (!str_starts_with($url, 'https://pbs.twimg.com/media/')) return '';
    return filter_var($url, FILTER_VALIDATE_URL) ? $url : '';
}

function ds_extract_post_image(string $content): string {
    $content = ds_normalize_x_html($content);

    $metaPatterns = [
        '~<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image(?::src)?)["\'][^>]+content=["\']([^"\']+)["\'][^>]*>~i',
        '~<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image(?::src)?)["\'][^>]*>~i',
    ];
    foreach ($metaPatterns as $pattern) {
        if (!preg_match_all($pattern, $content, $matches)) continue;
        foreach ($matches[1] ?? [] as $candidate) {
            $url = ds_media_candidate((string)$candidate);
            if ($url !== '') return $url;
        }
    }

    if (preg_match_all('~https://pbs\.twimg\.com/media/[^\s"\'<>\\]+~i', $content, $matches)) {
        foreach ($matches[0] ?? [] as $candidate) {
            $url = ds_media_candidate((string)$candidate);
            if ($url !== '') return $url;
        }
    }

    return '';
}

function ds_fetch_post_image(string $url): string {
    $content = ds_fetch_public_x_html($url, 18);
    if (!is_string($content) || $content === '') return '';
    return ds_extract_post_image($content);
}

function ds_build_posts(array $statuses, string $avatar): array {
    $posts = [];

    foreach ($statuses as $id => $url) {
        $embed = ds_fetch_oembed($url);
        if (!is_array($embed) || empty($embed['html'])) continue;

        $postHtml = ds_safe_post_html((string)$embed['html']);
        if ($postHtml === '') continue;

        $posts[] = [
            'id' => (string)$id,
            'url' => $url,
            'created_at' => ds_snowflake_time((string)$id),
            'name' => DS_X_NAME,
            'screen_name' => DS_X_HANDLE,
            'avatar' => $avatar,
            'html' => $postHtml,
            'image_url' => ds_fetch_post_image($url),
        ];
    }

    usort($posts, static function (array $a, array $b): int {
        $aId = (string)($a['id'] ?? '');
        $bId = (string)($b['id'] ?? '');
        if (strlen($aId) !== strlen($bId)) return strlen($bId) <=> strlen($aId);
        return strcmp($bId, $aId);
    });

    return array_slice($posts, 0, DS_X_MAX_ITEMS);
}

function ds_cache_is_fresh(?array $cache): bool {
    return is_array($cache)
        && (int)($cache['version'] ?? 0) === DS_X_CACHE_VERSION
        && isset($cache['fetched_at'])
        && (time() - (int)$cache['fetched_at'] < DS_X_CACHE_TTL)
        && !empty($cache['posts']);
}

function ds_refresh_cache(string $cacheFile, string $lockFile, string $profileUrl): ?array {
    $cache = ds_read_cache($cacheFile);
    if (ds_cache_is_fresh($cache)) return $cache;

    $lock = @fopen($lockFile, 'c');
    if (!$lock) return $cache;
    if (!@flock($lock, LOCK_EX | LOCK_NB)) {
        fclose($lock);
        return $cache;
    }

    $cache = ds_read_cache($cacheFile);
    if (!ds_cache_is_fresh($cache)) {
        $content = ds_fetch_public_x_html($profileUrl);
        if (is_string($content) && $content !== '') {
            $statuses = ds_extract_statuses($content);
            $avatar = ds_extract_profile_avatar($content);
            if ($avatar === '' && is_array($cache) && !empty($cache['avatar'])) {
                $avatar = (string)$cache['avatar'];
            }

            $posts = ds_build_posts($statuses, $avatar);
            if ($posts) {
                $cache = [
                    'version' => DS_X_CACHE_VERSION,
                    'source' => 'x-profile-initial-html',
                    'fetched_at' => time(),
                    'handle' => DS_X_HANDLE,
                    'avatar' => $avatar,
                    'status_count' => count($statuses),
                    'posts' => $posts,
                ];
                ds_write_cache($cacheFile, $cache);
            }
        }
    }

    @flock($lock, LOCK_UN);
    fclose($lock);
    return $cache;
}

function h(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function ds_time_label(string $raw): string {
    if ($raw === '') return '';
    $ts = strtotime($raw);
    if (!$ts) return '';
    $delta = max(0, time() - $ts);
    if ($delta < 60) return 'now';
    if ($delta < 3600) return max(1, intdiv($delta, 60)) . 'm';
    if ($delta < 86400) return max(1, intdiv($delta, 3600)) . 'h';
    if ($delta < 604800) return max(1, intdiv($delta, 86400)) . 'd';
    return gmdate('M j', $ts);
}

$cache = ds_refresh_cache($cacheFile, $lockFile, $profileUrl);
$posts = is_array($cache['posts'] ?? null) ? $cache['posts'] : [];
$stale = $cache && isset($cache['fetched_at']) ? max(0, time() - (int)$cache['fetched_at']) : null;
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Once Human X Feed</title>
<style>
:root{color-scheme:dark;--bg:#07090b;--line:#202a30;--text:#eef2f4;--muted:#85939b;--cyan:#58c7cc;--red:#e6323e}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI",system-ui,sans-serif}body{overflow-x:hidden}.feed{display:grid}.tweet{position:relative;display:grid;grid-template-columns:42px 1fr;gap:11px;padding:15px 16px;border-bottom:1px solid var(--line);background:linear-gradient(90deg,rgba(255,255,255,.018),transparent);color:inherit;transition:background .15s ease}.tweet:hover{background:linear-gradient(90deg,rgba(230,50,62,.055),rgba(88,199,204,.025))}.avatar-link{display:block;width:42px;height:42px}.avatar{width:42px;height:42px;border-radius:50%;object-fit:cover;background:#151b1f;border:1px solid #2a343a}.avatar-fallback{display:grid;place-items:center;font-weight:900;color:var(--cyan)}.top{display:flex;align-items:center;min-width:0;gap:6px;font-size:13px;line-height:1.2}.author{min-width:0;text-decoration:none}.name{font-weight:850;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.handle,.dot,.time{color:var(--muted);white-space:nowrap}.time{text-decoration:none}.body{margin-top:5px;font-size:14px;line-height:1.45;word-break:break-word}.body a{color:#72d6da;text-decoration:none}.body a:hover{text-decoration:underline}.media-preview{display:block;margin-top:11px;border:1px solid #263138;border-radius:10px;overflow:hidden;background:#0b1013;text-decoration:none}.media-preview img{display:block;width:100%;max-height:270px;object-fit:cover;background:#090c0e;transition:transform .22s cubic-bezier(.16,1,.3,1),opacity .15s ease}.media-preview:hover img,.media-preview:focus-visible img{transform:scale(1.012);opacity:.94}.media-preview:focus-visible{outline:1px solid var(--cyan);outline-offset:2px}.actions{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px;color:#68767d;font-size:10px;letter-spacing:.08em;text-transform:uppercase}.view-x{color:#8ea0a8;text-decoration:none}.view-x:hover{color:#fff}.x-mark{position:absolute;right:14px;top:14px;color:#c7d0d4;font-size:15px;font-weight:900;text-decoration:none}.empty{min-height:340px;display:grid;place-content:center;gap:8px;padding:30px;text-align:center;color:var(--muted);font-size:12px;letter-spacing:.06em;text-transform:uppercase}.empty strong{color:var(--red)}.empty a{color:var(--cyan)}.cache-note{padding:7px 12px;border-top:1px solid var(--line);color:#607078;font-size:9px;text-align:right;letter-spacing:.08em;text-transform:uppercase}@media(max-width:520px){.tweet{grid-template-columns:36px 1fr;padding:13px}.avatar-link,.avatar{width:36px;height:36px}.body{font-size:13px}.media-preview img{max-height:220px}}@media(prefers-reduced-motion:reduce){.media-preview img{transition:none}}
</style>
</head>
<body>
<div class="feed">
<?php if (!$posts): ?>
  <div class="empty"><strong>Official X feed is warming up</strong><span>Dead Signal is reading the latest public @<?=h(DS_X_HANDLE)?> posts directly from X on this web server.</span><a href="https://x.com/<?=h(DS_X_HANDLE)?>" target="_blank" rel="noopener noreferrer">Open @<?=h(DS_X_HANDLE)?> on X</a></div>
<?php else: ?>
<?php foreach ($posts as $post): ?>
  <article class="tweet">
    <a class="avatar-link" href="https://x.com/<?=h(DS_X_HANDLE)?>" target="_blank" rel="noopener noreferrer">
      <?php if (!empty($post['avatar'])): ?>
        <img class="avatar" src="<?=h((string)$post['avatar'])?>" alt="<?=h(DS_X_NAME)?>" loading="lazy" referrerpolicy="no-referrer">
      <?php else: ?>
        <span class="avatar avatar-fallback">OH</span>
      <?php endif; ?>
    </a>
    <div>
      <div class="top"><a class="author" href="https://x.com/<?=h(DS_X_HANDLE)?>" target="_blank" rel="noopener noreferrer"><span class="name"><?=h(DS_X_NAME)?></span> <span class="handle">@<?=h(DS_X_HANDLE)?></span></a><span class="dot">·</span><a class="time" href="<?=h((string)$post['url'])?>" target="_blank" rel="noopener noreferrer"><?=h(ds_time_label((string)$post['created_at']))?></a></div>
      <div class="body"><?=$post['html']?></div>
      <?php if (!empty($post['image_url'])): ?>
        <a class="media-preview" href="<?=h((string)$post['url'])?>" target="_blank" rel="noopener noreferrer" aria-label="View this post image on X">
          <img src="<?=h((string)$post['image_url'])?>" alt="Image attached to this Once Human post" loading="lazy" decoding="async" referrerpolicy="no-referrer">
        </a>
      <?php endif; ?>
      <div class="actions"><span>Official Once Human</span><a class="view-x" href="<?=h((string)$post['url'])?>" target="_blank" rel="noopener noreferrer">View on X ↗</a></div>
    </div>
    <a class="x-mark" href="<?=h((string)$post['url'])?>" target="_blank" rel="noopener noreferrer" aria-label="View post on X">X</a>
  </article>
<?php endforeach; ?>
<?php endif; ?>
</div>
<?php if ($stale !== null): ?><div class="cache-note">Cached <?=h((string)max(1, intdiv($stale, 60)))?> min ago</div><?php endif; ?>
</body>
</html>