<?php
declare(strict_types=1);
/**
 * ============================================================
 *  WALL OF THANKS — PHP API  (Thanksgiving 2026)
 *  Deployed at: /vishal/wall-of-thanks/thanks-giving/api.php
 *  (its own folder — /vishal/wall-of-thanks/api.php runs the Halloween wall)
 *
 *  GET  api.php  -> all thanks, newest first
 *  POST api.php  -> { name, message, website, elapsedMs }
 *
 *  Storage: ONE plain text file -> data/messages.json
 *           (protected from direct web access by data/.htaccess)
 *
 *  No database, no build step, no monthly limits.
 * ============================================================
 */

/* ===================== CONFIG ===================== */

// Set to false on the closing date to seal the wall (form hides itself,
// existing thanks stay visible, the API answers 403 with CLOSED_MESSAGE).
const SUBMISSIONS_OPEN = true;

// Wording shown to visitors once the wall is sealed.
const CLOSED_MESSAGE =
    'The wall is closed for this Thanksgiving — thank you to everyone who shared a note. Every one of them stays here.';

const MAX_NAME_LENGTH          = 40;    // matches the Webflow maxlength
const MAX_MESSAGE_LENGTH       = 140;   // matches the Webflow maxlength
const MAX_MESSAGES_TO_RETURN   = 300;   // cards sent to the page per load
const MAX_MESSAGES_TO_KEEP     = 5000;  // oldest dropped beyond this
const DUPLICATE_WINDOW_SECONDS = 600;   // same name+message blocked for 10 min
const MIN_FILL_TIME_MS         = 2500;  // faster than this = bot
const THROTTLE_MIN_GAP_SECONDS = 15;    // min gap between posts from one IP
const THROTTLE_MAX_PER_HOUR    = 10;    // max posts per IP per hour
const IP_HASH_SALT             = 'wall-of-thanks-v1'; // change to any random text

/* ===================== SETUP ===================== */

$DATA_DIR      = __DIR__ . '/data';
$MESSAGES_FILE = $DATA_DIR . '/messages.json';
$THROTTLE_FILE = $DATA_DIR . '/throttle.json';

ini_set('display_errors', '0');           // never leak paths to visitors
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('Access-Control-Allow-Origin: *');  // the wall is public by design
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

$method = isset($_SERVER['REQUEST_METHOD']) ? strtoupper((string) $_SERVER['REQUEST_METHOD']) : 'GET';

if ($method === 'OPTIONS') {
    http_response_code(204);
    exit;
}

try {
    ensure_storage($DATA_DIR);

    if ($method === 'GET') {
        $messages = with_messages($MESSAGES_FILE, LOCK_SH, static function (array $data): array {
            return [$data, $data];
        });
        $messages = array_values(array_filter($messages, 'is_valid_record'));

        usort($messages, static function (array $a, array $b): int {
            return strcmp((string) ($b['timestamp'] ?? ''), (string) ($a['timestamp'] ?? ''));
        });

        json_out(200, [
            'ok'              => true,
            'total'           => count($messages),
            'submissionsOpen' => SUBMISSIONS_OPEN,
            'closedMessage'   => CLOSED_MESSAGE,
            'messages'        => array_map('public_record', array_slice($messages, 0, MAX_MESSAGES_TO_RETURN)),
        ]);
    }

    if ($method === 'POST') {
        // Wall sealed: refuse posts but never break viewing.
        if (!SUBMISSIONS_OPEN) {
            json_out(403, ['ok' => false, 'closed' => true, 'error' => CLOSED_MESSAGE]);
        }

        $payload = read_json_body();

        // 1) Honeypot: humans never see this field. Pretend success.
        if (isset($payload['website']) && trim((string) $payload['website']) !== '') {
            json_out(200, ['ok' => true]);
        }

        // 2) Submitted suspiciously fast = bot.
        $elapsed = isset($payload['elapsedMs']) ? (int) $payload['elapsedMs'] : 0;
        if ($elapsed > 0 && $elapsed < MIN_FILL_TIME_MS) {
            json_out(400, ['ok' => false, 'error' => 'Please take a moment, then try again.']);
        }

        // 3) Clean + validate
        $name    = clean_text((string) ($payload['name'] ?? ''), MAX_NAME_LENGTH);
        $message = clean_text((string) ($payload['message'] ?? ''), MAX_MESSAGE_LENGTH);

        if ($message === '') {
            json_out(400, ['ok' => false, 'error' => 'Add a line about what you are thankful for.']);
        }
        if (!is_valid_utf8($name) || !is_valid_utf8($message)) {
            json_out(400, ['ok' => false, 'error' => 'Please use plain text characters.']);
        }
        if ($name === '') {
            $name = 'Someone';
        }

        $record = [
            'id'            => bin2hex(random_bytes(8)),
            'name'          => $name,
            'message'       => $message,
            'timestamp'     => gmdate('c'),
            'thanksgiving'  => '2026',
        ];

        // 4) Duplicate check first (read-only, so it never costs a throttle slot)
        $isDuplicate = with_messages(
            $MESSAGES_FILE,
            LOCK_SH,
            static function (array $data) use ($name, $message): array {
                return [$data, has_recent_duplicate($data, $name, $message)];
            }
        );
        if ($isDuplicate) {
            json_out(409, ['ok' => false, 'error' => 'That note is already on the wall — thank you!']);
        }

        // 5) Per-IP rate limit (checked BEFORE saving, so blocked posts never appear)
        $throttleError = throttle_check($THROTTLE_FILE, client_ip_hash(), time());
        if ($throttleError !== null) {
            json_out(429, ['ok' => false, 'error' => $throttleError]);
        }

        // 6) Save, inside one exclusive lock
        $result = with_messages(
            $MESSAGES_FILE,
            LOCK_EX,
            static function (array $data) use ($record): array {
                // Re-check duplicates inside the lock (belt and braces)
                if (has_recent_duplicate($data, (string) $record['name'], (string) $record['message'])) {
                    return [$data, ['status' => 'duplicate']];
                }

                array_unshift($data, $record);               // newest first
                if (count($data) > MAX_MESSAGES_TO_KEEP) {
                    $data = array_slice($data, 0, MAX_MESSAGES_TO_KEEP);
                }
                return [$data, ['status' => 'saved']];
            }
        );

        if ($result['status'] === 'duplicate') {
            json_out(409, ['ok' => false, 'error' => 'That note is already on the wall — thank you!']);
        }

        json_out(201, ['ok' => true, 'message' => public_record($record)]);
    }

    json_out(405, ['ok' => false, 'error' => 'Method not allowed.']);
} catch (Throwable $e) {
    error_log('[wall-of-thanks] ' . $e->getMessage());
    json_out(500, [
        'ok'    => false,
        'error' => 'The wall storage is not writable on this server. Make sure the "data" folder exists and is writable (permissions 755), then try again.',
    ]);
}

/* ===================== FUNCTIONS ===================== */

function json_out(int $status, array $payload): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/** Create the data folder, its .htaccess guard and index.html if missing. */
function ensure_storage(string $dir): void
{
    if (!is_dir($dir)) {
        if (!@mkdir($dir, 0755, true) && !is_dir($dir)) {
            throw new RuntimeException('Cannot create data directory: ' . $dir);
        }
    }

    $htaccess = $dir . '/.htaccess';
    if (!file_exists($htaccess)) {
        @file_put_contents($htaccess,
            "# Block all direct web access to this folder\n" .
            "<IfModule mod_authz_core.c>\n  Require all denied\n</IfModule>\n" .
            "<IfModule !mod_authz_core.c>\n  Order allow,deny\n  Deny from all\n</IfModule>\n"
        );
    }

    $index = $dir . '/index.html';
    if (!file_exists($index)) {
        @file_put_contents($index, '');
    }
}

/**
 * Lock -> read -> callback -> (optionally) atomic write -> unlock.
 * Uses a separate .lock file so the JSON can be replaced atomically.
 *
 * @return mixed callback result
 */
function with_messages(string $file, int $lockType, callable $fn)
{
    $lockHandle = @fopen($file . '.lock', 'c');
    if ($lockHandle === false) {
        throw new RuntimeException('Cannot open lock file');
    }
    if (!flock($lockHandle, $lockType)) {
        fclose($lockHandle);
        throw new RuntimeException('Cannot lock data file');
    }

    try {
        $data = read_json_file($file);
        $data = array_values($data);          // thanks are a simple list
        [$data, $result] = $fn($data);

        if ($lockType === LOCK_EX) {
            write_json_file($file, $data);
        }
    } finally {
        flock($lockHandle, LOCK_UN);
        fclose($lockHandle);
    }

    return $result;
}

/** Returns the decoded JSON as-is (keeps array keys when they are keys). */
function read_json_file(string $file): array
{
    if (!file_exists($file)) {
        return [];
    }
    $raw = @file_get_contents($file);
    if ($raw === false || trim($raw) === '') {
        return [];
    }
    $decoded = json_decode($raw, true);
    if (!is_array($decoded)) {
        // Corrupt file: back it up rather than overwrite it blindly.
        @copy($file, $file . '.corrupt-' . time() . '.bak');
        return [];
    }
    return $decoded;
}

/** True if the same name + message was posted inside the duplicate window. */
function has_recent_duplicate(array $data, string $name, string $message): bool
{
    $normName    = normalize($name);
    $normMessage = normalize($message);
    $now         = time();

    foreach ($data as $existing) {
        if (!is_array($existing)) {
            continue;
        }
        $ts = isset($existing['timestamp']) ? strtotime((string) $existing['timestamp']) : false;
        if ($ts !== false
            && ($now - $ts) <= DUPLICATE_WINDOW_SECONDS
            && normalize((string) ($existing['name'] ?? '')) === $normName
            && normalize((string) ($existing['message'] ?? '')) === $normMessage
        ) {
            return true;
        }
    }
    return false;
}

/** Writes to a temp file then renames — never leaves half a file. */
function write_json_file(string $file, array $data): void
{
    $json = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    if ($json === false) {
        throw new RuntimeException('Cannot encode thanks to JSON');
    }
    $tmp = $file . '.tmp';
    if (@file_put_contents($tmp, $json) === false) {
        throw new RuntimeException('Cannot write temp data file');
    }
    if (!@rename($tmp, $file)) {
        @unlink($tmp);
        throw new RuntimeException('Cannot replace data file');
    }
    @chmod($file, 0644);
}

/**
 * Per-IP rate limit stored in data/throttle.json
 * @return string|null error message, or null when allowed
 */
function throttle_check(string $file, string $ipHash, int $now): ?string
{
    $handle = @fopen($file . '.lock', 'c');
    if ($handle === false) {
        return null; // fail open: never block a real visitor over a lock
    }
    if (!flock($handle, LOCK_EX)) {
        fclose($handle);
        return null;
    }

    try {
        $store = read_json_file($file);
        $stamps = [];
        if (isset($store[$ipHash]) && is_array($store[$ipHash])) {
            foreach ($store[$ipHash] as $t) {
                $t = (int) $t;
                if ($t > ($now - 3600)) {
                    $stamps[] = $t;   // keep only the past hour
                }
            }
        }

        $last = $stamps ? (int) max($stamps) : 0;
        if ($last > 0 && ($now - $last) < THROTTLE_MIN_GAP_SECONDS) {
            return 'Please wait a few seconds before posting again.';
        }
        if (count($stamps) >= THROTTLE_MAX_PER_HOUR) {
            return 'Too many notes from this connection. Please try again in a while.';
        }

        $stamps[] = $now;
        $store[$ipHash] = $stamps;

        // Prune IPs that have gone quiet so the file stays tiny
        foreach ($store as $key => $list) {
            if (!is_array($list)) {
                unset($store[$key]);
                continue;
            }
            $fresh = array_filter($list, static function ($t) use ($now): bool {
                return ((int) $t) > ($now - 3600);
            });
            if (!$fresh) {
                unset($store[$key]);
            } else {
                $store[$key] = array_values($fresh);
            }
        }

        write_json_file($file, $store);
    } finally {
        flock($handle, LOCK_UN);
        fclose($handle);
    }

    return null;
}

function read_json_body(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === false || trim($raw) === '') {
        return [];
    }
    if (strlen($raw) > 12000) {
        json_out(413, ['ok' => false, 'error' => 'Note is too large.']);
    }
    $decoded = json_decode($raw, true);
    if (!is_array($decoded)) {
        json_out(400, ['ok' => false, 'error' => 'Invalid request.']);
    }
    return $decoded;
}

/** Collapse whitespace, strip control characters, clamp length. */
function clean_text(string $value, int $maxLength): string
{
    $value = (string) preg_replace('/[\x00-\x1F\x7F]+/u', ' ', $value);
    $value = (string) preg_replace('/\s+/u', ' ', $value);
    $value = trim($value);

    if (function_exists('mb_substr')) {
        return mb_substr($value, 0, $maxLength, 'UTF-8');
    }
    return substr($value, 0, $maxLength);
}

function normalize(string $value): string
{
    $value = trim((string) preg_replace('/\s+/u', ' ', $value));
    if (function_exists('mb_strtolower')) {
        return mb_strtolower($value, 'UTF-8');
    }
    return strtolower($value);
}

function is_valid_utf8(string $value): bool
{
    if (function_exists('mb_check_encoding')) {
        return mb_check_encoding($value, 'UTF-8');
    }
    return (bool) preg_match('//u', $value);
}

function is_valid_record($item): bool
{
    return is_array($item)
        && isset($item['name'], $item['message'])
        && is_string($item['name'])
        && is_string($item['message']);
}

/** Only these fields ever leave the server. */
function public_record(array $item): array
{
    return [
        'id'        => (string) ($item['id'] ?? ''),
        'name'      => (string) ($item['name'] ?? ''),
        'message'   => (string) ($item['message'] ?? ''),
        'timestamp' => (string) ($item['timestamp'] ?? ''),
    ];
}

/** Hashed so raw visitor IPs are never stored. */
function client_ip_hash(): string
{
    $ip = isset($_SERVER['REMOTE_ADDR']) ? (string) $_SERVER['REMOTE_ADDR'] : 'unknown';
    return substr(hash('sha256', IP_HASH_SALT . '|' . $ip), 0, 32);
}
