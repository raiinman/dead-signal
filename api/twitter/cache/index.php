<?php
declare(strict_types=1);

const DS_X_HANDLE = 'OnceHuman_';
const DS_X_CACHE_TTL = 600;
const DS_X_MAX_ITEMS = 8;
const DS_X_CANDIDATE_LIMIT = 500;
const DS_X_CACHE_VERSION = 2;

$cacheFile = __DIR__ . '/timeline-cache.json';
$lockFile = __DIR__ . '/timeline-cache.lock';
$sourceUrl = 'https://syndication.twitter.com/srv/timeline-profile/screen-name/' . rawurlencode(DS_X_HANDLE);

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

function ds_fetch(string $url): ?string {
    if (!function_exists('curl_init')) return null;
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_TIMEOUT => 15,
        CURLOPT_ENCODING => '',
        CURLOPT_HTTPHEADER => [
            'Accept: text/html,application/xhtml+xml',
            'Accept-Language: en-US,en;q=0.9',
            'Cache-Control: no-cache',
        ],
        CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36 DeadSignal/1.0',
    ]);
    $body = curl_exec($ch);
    $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);
    if (!is_string($body) || $status !== 200 || $body === '') return null;
    return $body;
}

function ds_find_tweets(mixed $node, array &$tweets): void {
    if (!is_array($node) || count($tweets) >= DS_X_CANDIDATE_LIMIT) return;

    if (isset($node['tweet']) && is_array($node['tweet'])) {
        $tweets[] = $node['tweet'];
    }

    foreach ($node as $value) {
        if (is_array($value)) ds_find_tweets($value, $tweets);
        if (count($tweets) >= DS_X_CANDIDATE_LIMIT) break;
    }
}

function ds_first_string(array $data, array $keys): string {
    foreach ($keys as $key) {
        if (isset($data[$key]) && is_string($data[$key]) && trim($data[$key]) !== '') {
            return trim($data[$key]);
        }
    }
    return '';
}

function ds_user_from_tweet(array $tweet): array {
    $candidates = [];
    if (isset($tweet['user']) && is_array($tweet['user'])) $candidates[] = $tweet['user'];
    if (isset($tweet['user_results']['result']) && is_array($tweet['user_results']['result'])) $candidates[] = $tweet['user_results']['result'];
    if (isset($tweet['core']['user_results']['result']) && is_array($tweet['core']['user_results']['result'])) $candidates[] = $tweet['core']['user_results']['result'];

    foreach ($candidates as $user) {
        $legacy = isset($user['legacy']) && is_array($user['legacy']) ? $user['legacy'] : $user;
        $name = ds_first_string($legacy, ['name']);
        $screen = ds_first_string($legacy, ['screen_name', 'screenName']);
        $avatar = ds_first_string($legacy, ['profile_image_url_https', 'profile_image_url']);
        if ($name !== '' || $screen !== '') {
            return ['name' => $name ?: $screen, 'screen_name' => $screen ?: DS_X_HANDLE, 'avatar' => $avatar];
        }
    }

    return ['name' => 'Once Human', 'screen_name' => DS_X_HANDLE, 'avatar' => ''];
}

function ds_media_from_tweet(array $tweet): array {
    $media = [];
    $sources = [];
    if (isset($tweet['mediaDetails']) && is_array($tweet['mediaDetails'])) $sources[] = $tweet['mediaDetails'];
    if (isset($tweet['extended_entities']['media']) && is_array($tweet['extended_entities']['media'])) $sources[] = $tweet['extended_entities']['media'];
    if (isset($tweet['entities']['media']) && is_array($tweet['entities']['media'])) $sources[] = $tweet['entities']['media'];

    foreach ($sources as $items) {
        foreach ($items as $item) {
            if (!is_array($item)) continue;
            $url = ds_first_string($item, ['media_url_https', 'media_url', 'url']);
            if ($url !== '' && str_starts_with($url, 'http')) $media[] = $url;
            if (count($media) >= 4) break 2;
        }
    }
    return array_values(array_unique($media));
}

function ds_normalize_tweets(array $rawTweets): array {
    $out = [];
    $seen = [];

    foreach ($rawTweets as $tweet) {
        if (!is_array($tweet)) continue;
        $legacy = isset($tweet['legacy']) && is_array($tweet['legacy']) ? $tweet['legacy'] : $tweet;
        $text = ds_first_string($legacy, ['full_text', 'text']);
        if ($text === '') continue;

        $user = ds_user_from_tweet($tweet);
        $screen = $user['screen_name'] ?: DS_X_HANDLE;
        if (strcasecmp($screen, DS_X_HANDLE) !== 0) continue;

        $id = ds_first_string($legacy, ['id_str']);
        if ($id === '' && isset($tweet['rest_id'])) $id = (string) $tweet['rest_id'];
        if ($id === '' && isset($tweet['id_str'])) $id = (string) $tweet['id_str'];
        if ($id === '') $id = sha1($text);
        if (isset($seen[$id])) continue;
        $seen[$id] = true;

        $createdAt = ds_first_string($legacy, ['created_at']);
        $sortTs = $createdAt !== '' ? strtotime($createdAt) : false;
        $url = ctype_digit($id) ? 'https://x.com/' . rawurlencode($screen) . '/status/' . $id : 'https://x.com/' . rawurlencode($screen);

        $out[] = [
            'id' => $id,
            'text' => $text,
            'created_at' => $createdAt,
            'name' => $user['name'],
            'screen_name' => $screen,
            'avatar' => $user['avatar'],
            'url' => $url,
            'media' => ds_media_from_tweet($legacy + $tweet),
            'reply_count' => (int)($legacy['reply_count'] ?? 0),
            'retweet_count' => (int)($legacy['retweet_count'] ?? 0),
            'favorite_count' => (int)($legacy['favorite_count'] ?? 0),
            '_sort_ts' => $sortTs === false ? 0 : $sortTs,
        ];
    }

    usort($out, static function (array $a, array $b): int {
        $timeCompare = ((int)$b['_sort_ts']) <=> ((int)$a['_sort_ts']);
        if ($timeCompare !== 0) return $timeCompare;
        return strcmp((string)$b['id'], (string)$a['id']);
    });

    $out = array_slice($out, 0, DS_X_MAX_ITEMS);
    foreach ($out as &$tweet) unset($tweet['_sort_ts']);
    unset($tweet);
    return $out;
}

function ds_parse_syndication(string $html): array {
    if (!preg_match('~<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>~si', $html, $m)) return [];
    $json = html_entity_decode($m[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $data = json_decode($json, true);
    if (!is_array($data)) return [];
    $tweets = [];
    ds_find_tweets($data, $tweets);
    return ds_normalize_tweets($tweets);
}

function ds_cache_is_fresh(?array $cache): bool {
    return is_array($cache)
        && (int)($cache['version'] ?? 0) === DS_X_CACHE_VERSION
        && isset($cache['fetched_at'])
        && (time() - (int)$cache['fetched_at'] < DS_X_CACHE_TTL)
        && !empty($cache['tweets']);
}

function ds_refresh_cache(string $sourceUrl, string $cacheFile, string $lockFile): ?array {
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
        $html = ds_fetch($sourceUrl);
        $tweets = $html ? ds_parse_syndication($html) : [];
        if ($tweets) {
            $cache = [
                'version' => DS_X_CACHE_VERSION,
                'fetched_at' => time(),
                'handle' => DS_X_HANDLE,
                'tweets' => $tweets,
            ];
            ds_write_cache($cacheFile, $cache);
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
    $delta = time() - $ts;
    if ($delta < 60) return 'now';
    if ($delta < 3600) return max(1, intdiv($delta, 60)) . 'm';
    if ($delta < 86400) return max(1, intdiv($delta, 3600)) . 'h';
    if ($delta < 604800) return max(1, intdiv($delta, 86400)) . 'd';
    return gmdate('M j', $ts);
}

$cache = ds_refresh_cache($sourceUrl, $cacheFile, $lockFile);
$tweets = is_array($cache['tweets'] ?? null) ? $cache['tweets'] : [];
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
:root{color-scheme:dark;--bg:#07090b;--panel:#0b0f12;--line:#202a30;--text:#eef2f4;--muted:#85939b;--cyan:#58c7cc;--red:#e6323e}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI",system-ui,sans-serif}body{overflow-x:hidden}.feed{display:grid}.tweet{display:grid;grid-template-columns:42px 1fr;gap:11px;padding:15px 16px;border-bottom:1px solid var(--line);background:linear-gradient(90deg,rgba(255,255,255,.018),transparent);text-decoration:none;color:inherit;transition:background .15s ease}.tweet:hover{background:linear-gradient(90deg,rgba(230,50,62,.055),rgba(88,199,204,.025))}.avatar{width:42px;height:42px;border-radius:50%;object-fit:cover;background:#151b1f;border:1px solid #2a343a}.avatar-fallback{display:grid;place-items:center;font-weight:900;color:var(--cyan)}.top{display:flex;align-items:center;min-width:0;gap:6px;font-size:13px;line-height:1.2}.name{font-weight:850;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.handle,.dot,.time{color:var(--muted);white-space:nowrap}.body{margin-top:5px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-break:break-word}.media{margin-top:10px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px;border:1px solid #263138;border-radius:10px;overflow:hidden;background:#0d1215}.media.one{grid-template-columns:1fr}.media img{display:block;width:100%;height:150px;object-fit:cover;background:#11171a}.media.one img{height:220px}.stats{display:flex;gap:18px;margin-top:9px;color:#6f7d84;font-size:11px}.stats b{color:#91a0a7;font-weight:700}.empty{min-height:340px;display:grid;place-content:center;gap:8px;padding:30px;text-align:center;color:var(--muted);font-size:12px;letter-spacing:.06em;text-transform:uppercase}.empty strong{color:var(--red)}.empty a{color:var(--cyan)}.cache-note{padding:7px 12px;border-top:1px solid var(--line);color:#607078;font-size:9px;text-align:right;letter-spacing:.08em;text-transform:uppercase}@media(max-width:520px){.tweet{grid-template-columns:36px 1fr;padding:13px}.avatar{width:36px;height:36px}.body{font-size:13px}.media img,.media.one img{height:150px}}
</style>
</head>
<body>
<div class="feed">
<?php if (!$tweets): ?>
  <div class="empty"><strong>Official X feed is warming up</strong><span>Dead Signal will serve a cached timeline as soon as X responds.</span><a href="https://x.com/<?=h(DS_X_HANDLE)?>" target="_blank" rel="noopener noreferrer">Open @<?=h(DS_X_HANDLE)?> on X</a></div>
<?php else: ?>
<?php foreach ($tweets as $tweet): ?>
  <a class="tweet" href="<?=h((string)$tweet['url'])?>" target="_blank" rel="noopener noreferrer">
    <?php if (!empty($tweet['avatar'])): ?>
      <img class="avatar" src="<?=h((string)$tweet['avatar'])?>" alt="" loading="lazy" referrerpolicy="no-referrer">
    <?php else: ?>
      <span class="avatar avatar-fallback">OH</span>
    <?php endif; ?>
    <div>
      <div class="top"><span class="name"><?=h((string)$tweet['name'])?></span><span class="handle">@<?=h((string)$tweet['screen_name'])?></span><span class="dot">·</span><span class="time"><?=h(ds_time_label((string)$tweet['created_at']))?></span></div>
      <div class="body"><?=h((string)$tweet['text'])?></div>
      <?php if (!empty($tweet['media'])): ?>
      <div class="media <?=count($tweet['media']) === 1 ? 'one' : ''?>">
        <?php foreach ($tweet['media'] as $media): ?><img src="<?=h((string)$media)?>" alt="" loading="lazy" referrerpolicy="no-referrer"><?php endforeach; ?>
      </div>
      <?php endif; ?>
      <div class="stats"><span>↩ <b><?=number_format((int)$tweet['reply_count'])?></b></span><span>↻ <b><?=number_format((int)$tweet['retweet_count'])?></b></span><span>♥ <b><?=number_format((int)$tweet['favorite_count'])?></b></span></div>
    </div>
  </a>
<?php endforeach; ?>
<?php endif; ?>
</div>
<?php if ($stale !== null): ?><div class="cache-note">Cached <?=h((string)max(1, intdiv($stale, 60)))?> min ago</div><?php endif; ?>
</body>
</html>
