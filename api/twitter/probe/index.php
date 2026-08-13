<?php
declare(strict_types=1);

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store, max-age=0');
header('X-Content-Type-Options: nosniff');

const DS_PROBE_URL = 'https://x.com/OnceHuman_';

function line(string $label, string $value): void {
    echo str_pad($label, 28) . $value . "\n";
}

function clip(string $value, int $limit = 500): string {
    $value = preg_replace('/\s+/u', ' ', trim($value)) ?? trim($value);
    if (mb_strlen($value, 'UTF-8') <= $limit) return $value;
    return mb_substr($value, 0, $limit, 'UTF-8') . '…';
}

function marker_snippet(string $haystack, string $needle, int $radius = 220): string {
    $pos = stripos($haystack, $needle);
    if ($pos === false) return '';
    $start = max(0, $pos - $radius);
    return clip(substr($haystack, $start, ($radius * 2) + strlen($needle)), 480);
}

echo "DEAD SIGNAL — SERVER X PROFILE PROBE\n";
echo "====================================\n";
line('Target:', DS_PROBE_URL);
line('PHP:', PHP_VERSION);
line('cURL available:', function_exists('curl_init') ? 'yes' : 'no');
line('DOMDocument available:', class_exists('DOMDocument') ? 'yes' : 'no');
line('shell_exec available:', function_exists('shell_exec') ? 'yes' : 'no');
echo "\n";

if (!function_exists('curl_init')) {
    echo "RESULT: FAIL — PHP cURL is unavailable on this hosting account.\n";
    exit;
}

$headers = [];
$ch = curl_init(DS_PROBE_URL);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => true,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_TIMEOUT => 35,
    CURLOPT_ENCODING => '',
    CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
    CURLOPT_HTTPHEADER => [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language: en-US,en;q=0.9',
        'Cache-Control: no-cache',
        'Pragma: no-cache',
        'Sec-Fetch-Dest: document',
        'Sec-Fetch-Mode: navigate',
        'Sec-Fetch-Site: none',
        'Upgrade-Insecure-Requests: 1',
    ],
    CURLOPT_HEADERFUNCTION => static function ($curl, string $header) use (&$headers): int {
        $len = strlen($header);
        $parts = explode(':', $header, 2);
        if (count($parts) === 2) {
            $headers[strtolower(trim($parts[0]))] = trim($parts[1]);
        }
        return $len;
    },
]);

$body = curl_exec($ch);
$error = curl_error($ch);
$status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
$finalUrl = (string)curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
$contentType = (string)curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
curl_close($ch);

line('HTTP status:', (string)$status);
line('Final URL:', $finalUrl ?: '(none)');
line('Content-Type:', $contentType ?: '(none)');
line('Response bytes:', is_string($body) ? number_format(strlen($body)) : '0');
line('cURL error:', $error !== '' ? $error : '(none)');
line('Server header:', $headers['server'] ?? '(not exposed)');
echo "\n";

if (!is_string($body) || $body === '' || $status < 200 || $status >= 400) {
    echo "RESULT: FAIL — Namecheap did not receive a usable X profile document.\n";
    exit;
}

$decoded = html_entity_decode($body, ENT_QUOTES | ENT_HTML5, 'UTF-8');
$plain = strip_tags($decoded);
$plain = preg_replace('/\s+/u', ' ', $plain) ?? $plain;

$markers = [
    'Once Human',
    '@OnceHuman_',
    'Pinned',
    '13 days until console launch',
    'Fashion Set Custom Dye Optimization',
    'Version 3.0.3 Bug Fixes',
    'Very Positive on Steam',
];

echo "MARKERS IN INITIAL HTML\n";
echo "-----------------------\n";
foreach ($markers as $marker) {
    line($marker . ':', stripos($decoded, $marker) !== false ? 'FOUND' : 'not found');
}
echo "\n";

preg_match_all('~(?:https?:\\/\\/(?:www\\.)?x\\.com)?\\/OnceHuman_\\/status\\/(\\d+)~i', $decoded, $matches);
$statusIds = array_values(array_unique($matches[1] ?? []));
usort($statusIds, static function (string $a, string $b): int {
    if (strlen($a) !== strlen($b)) return strlen($b) <=> strlen($a);
    return strcmp($b, $a);
});
line('Status IDs found:', (string)count($statusIds));
if ($statusIds) {
    echo 'Newest IDs: ' . implode(', ', array_slice($statusIds, 0, 12)) . "\n";
}

echo "\nSTRUCTURE HINTS\n";
echo "---------------\n";
foreach (['full_text', 'created_at', 'rest_id', 'tweet_results', '__NEXT_DATA__', 'application/ld+json'] as $hint) {
    line($hint . ':', (string)substr_count($decoded, $hint));
}

echo "\nVISIBLE-TEXT SNIPPETS\n";
echo "---------------------\n";
$shown = 0;
foreach ($markers as $marker) {
    $snippet = marker_snippet($plain, $marker);
    if ($snippet === '') continue;
    echo '[' . $marker . "]\n" . $snippet . "\n\n";
    $shown++;
    if ($shown >= 5) break;
}

if (function_exists('shell_exec')) {
    echo "SERVER RUNTIME CHECK\n";
    echo "--------------------\n";
    foreach (['node', 'python3', 'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'] as $binary) {
        $safe = escapeshellarg($binary);
        $path = trim((string)@shell_exec('command -v ' . $safe . ' 2>/dev/null'));
        line($binary . ':', $path !== '' ? 'available' : 'not found');
    }
    echo "\n";
}

if (stripos($decoded, '13 days until console launch') !== false || stripos($decoded, 'Version 3.0.3 Bug Fixes') !== false) {
    echo "RESULT: PROMISING — the Namecheap server can see current timeline content in X's initial HTML.\n";
} elseif ($statusIds) {
    echo "RESULT: PARTIAL — the server can see X status IDs, but current visible-post text was not confirmed.\n";
} else {
    echo "RESULT: BLOCKED — direct server fetch does not expose the current public timeline.\n";
}
