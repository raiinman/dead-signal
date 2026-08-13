<?php
declare(strict_types=1);

const DS_X_HANDLE = 'OnceHuman_';
const DS_X_CACHE_TTL = 300;
const DS_X_MAX_ITEMS = 8;
const DS_X_CACHE_VERSION = 3;

$cacheFile = __DIR__ . '/timeline-cache.json';
$lockFile = __DIR__ . '/timeline-cache.lock';

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

function ds_load_bearer_token(): string {
    $env = trim((string)getenv('DEAD_SIGNAL_X_BEARER_TOKEN'));
    if ($env !== '') return $env;

    $docRoot = (string)($_SERVER['DOCUMENT_ROOT'] ?? '');
    if ($docRoot !== '') {
        $secretFile = dirname($docRoot) . '/dead-signal-secrets/x-api.php';
        if (is_file($secretFile)) {
            $secret = include $secretFile;
            if (is_array($secret) && isset($secret['bearer_token'])) {
                return trim((string)$secret['bearer_token']);
            }
        }
    }

    return '';
}

function ds_api_get(string $url, string $token): ?array {
    if ($token === '' || !function_exists('curl_init')) return null;

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_TIMEOUT => 15,
        CURLOPT_ENCODING => '',
        CURLOPT_HTTPHEADER => [
            'Accept: application/json',
            'Authorization: Bearer ' . $token,
        ],
        CURLOPT_USERAGENT => 'DeadSignal/1.0 (+https://deadsignaldb.com/)',
    ]);

    $body = curl_exec($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);

    if (!is_string($body) || $status < 200 || $status >= 300) return null;
    $data = json_decode($body, true);
    return is_array($data) ? $data : null;
}

function ds_media_map(array $payload): array {
    $map = [];
    foreach (($payload['includes']['media'] ?? []) as $media) {
        if (!is_array($media) || empty($media['media_key'])) continue;
        $url = '';
        if (($media['type'] ?? '') === 'photo') {
            $url = (string)($media['url'] ?? '');
        } else {
            $url = (string)($media['preview_image_url'] ?? '');
        }
        if ($url !== '') $map[(string)$media['media_key']] = $url;
    }
    return $map;
}

function ds_normalize_api_tweets(array $payload, array $profile): array {
    $out = [];
    $mediaMap = ds_media_map($payload);

    foreach (($payload['data'] ?? []) as $tweet) {
        if (!is_array($tweet) || empty($tweet['id']) || empty($tweet['text'])) continue;

        $media = [];
        foreach (($tweet['attachments']['media_keys'] ?? []) as $key) {
            if (isset($mediaMap[$key])) $media[] = $mediaMap[$key];
        }

        $metrics = is_array($tweet['public_metrics'] ?? null) ? $tweet['public_metrics'] : [];
        $id = (string)$tweet['id'];
        $out[] = [
            'id' => $id,
            'text' => (string)$tweet['text'],
            'created_at' => (string)($tweet['created_at'] ?? ''),
            'name' => (string)($profile['name'] ?? 'Once Human'),
            'screen_name' => (string)($profile['username'] ?? DS_X_HANDLE),
            'avatar' => (string)($profile['profile_image_url'] ?? ''),
            'url' => 'https://x.com/' . rawurlencode((string)($profile['username'] ?? DS_X_HANDLE)) . '/status/' . $id,
            'media' => array_slice(array_values(array_unique($media)), 0, 4),
            'reply_count' => (int)($metrics['reply_count'] ?? 0),
            'retweet_count' => (int)($metrics['retweet_count'] ?? 0),
            'favorite_count' => (int)($metrics['like_count'] ?? 0),
        ];

        if (count($out) >= DS_X_MAX_ITEMS) break;
    }

    return $out;
}

function ds_cache_is_fresh(?array $cache): bool {
    return is_array($cache)
        && (int)($cache['version'] ?? 0) === DS_X_CACHE_VERSION
        && isset($cache['fetched_at'])
        && (time() - (int)$cache['fetched_at'] < DS_X_CACHE_TTL)
        && !empty($cache['tweets']);
}

function ds_refresh_cache(string $cacheFile, string $lockFile, string $token): ?array {
    $cache = ds_read_cache($cacheFile);
    if (ds_cache_is_fresh($cache)) return $cache;
    if ($token === '') return null;

    $lock = @fopen($lockFile, 'c');
    if (!$lock) return $cache;
    if (!@flock($lock, LOCK_EX | LOCK_NB)) {
        fclose($lock);
        return $cache;
    }

    $cache = ds_read_cache($cacheFile);
    if (!ds_cache_is_fresh($cache)) {
        $profile = [];
        $userId = '';

        if (is_array($cache) && !empty($cache['user_id']) && is_array($cache['profile'] ?? null)) {
            $userId = (string)$cache['user_id'];
            $profile = $cache['profile'];
        }

        if ($userId === '') {
            $userUrl = 'https://api.x.com/2/users/by/username/' . rawurlencode(DS_X_HANDLE)
                . '?user.fields=name,username,profile_image_url';
            $userPayload = ds_api_get($userUrl, $token);
            if (is_array($userPayload['data'] ?? null)) {
                $profile = $userPayload['data'];
                $userId = (string)($profile['id'] ?? '');
            }
        }

        if ($userId !== '') {
            $query = http_build_query([
                'max_results' => 10,
                'exclude' => 'replies,retweets',
                'tweet.fields' => 'created_at,public_metrics,attachments',
                'expansions' => 'attachments.media_keys',
                'media.fields' => 'media_key,type,url,preview_image_url,width,height',
            ], '', '&', PHP_QUERY_RFC3986);
            $tweetsPayload = ds_api_get('https://api.x.com/2/users/' . rawurlencode($userId) . '/tweets?' . $query, $token);
            $tweets = is_array($tweetsPayload) ? ds_normalize_api_tweets($tweetsPayload, $profile) : [];

            if ($tweets) {
                $cache = [
                    'version' => DS_X_CACHE_VERSION,
                    'fetched_at' => time(),
                    'handle' => DS_X_HANDLE,
                    'user_id' => $userId,
                    'profile' => $profile,
                    'tweets' => $tweets,
                ];
                ds_write_cache($cacheFile, $cache);
            }
        }
    }

    @flock($lock, LOCK_UN);
    fclose($lock);
    return ds_cache_is_fresh($cache) ? $cache : null;
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

$token = ds_load_bearer_token();
$cache = ds_refresh_cache($cacheFile, $lockFile, $token);
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
:root{color-scheme:dark;--bg:#07090b;--line:#202a30;--text:#eef2f4;--muted:#85939b;--cyan:#58c7cc;--red:#e6323e}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI",system-ui,sans-serif}body{overflow-x:hidden}.feed{display:grid}.tweet{display:grid;grid-template-columns:42px 1fr;gap:11px;padding:15px 16px;border-bottom:1px solid var(--line);background:linear-gradient(90deg,rgba(255,255,255,.018),transparent);text-decoration:none;color:inherit;transition:background .15s ease}.tweet:hover{background:linear-gradient(90deg,rgba(230,50,62,.055),rgba(88,199,204,.025))}.avatar{width:42px;height:42px;border-radius:50%;object-fit:cover;background:#151b1f;border:1px solid #2a343a}.avatar-fallback{display:grid;place-items:center;font-weight:900;color:var(--cyan)}.top{display:flex;align-items:center;min-width:0;gap:6px;font-size:13px;line-height:1.2}.name{font-weight:850;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.handle,.dot,.time{color:var(--muted);white-space:nowrap}.body{margin-top:5px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-break:break-word}.media{margin-top:10px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px;border:1px solid #263138;border-radius:10px;overflow:hidden;background:#0d1215}.media.one{grid-template-columns:1fr}.media img{display:block;width:100%;height:150px;object-fit:cover;background:#11171a}.media.one img{height:220px}.stats{display:flex;gap:18px;margin-top:9px;color:#6f7d84;font-size:11px}.stats b{color:#91a0a7;font-weight:700}.empty{min-height:340px;display:grid;place-content:center;gap:8px;padding:30px;text-align:center;color:var(--muted);font-size:12px;letter-spacing:.06em;text-transform:uppercase}.empty strong{color:var(--red)}.empty a{color:var(--cyan)}.cache-note{padding:7px 12px;border-top:1px solid var(--line);color:#607078;font-size:9px;text-align:right;letter-spacing:.08em;text-transform:uppercase}@media(max-width:520px){.tweet{grid-template-columns:36px 1fr;padding:13px}.avatar{width:36px;height:36px}.body{font-size:13px}.media img,.media.one img{height:150px}}
</style>
</head>
<body>
<div class="feed">
<?php if (!$tweets): ?>
  <div class="empty">
    <?php if ($token === ''): ?>
      <strong>X API connection required</strong><span>The cached feed is ready; Dead Signal needs its private X bearer token configured on the server.</span>
    <?php else: ?>
      <strong>Official X feed is warming up</strong><span>Dead Signal could not retrieve the live timeline yet.</span>
    <?php endif; ?>
    <a href="https://x.com/<?=h(DS_X_HANDLE)?>" target="_blank" rel="noopener noreferrer">Open @<?=h(DS_X_HANDLE)?> on X</a>
  </div>
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
