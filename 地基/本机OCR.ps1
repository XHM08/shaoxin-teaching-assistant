# Shaoxin - local OCR: read text out of an image, using the Windows built-in engine
# (Windows.Media.Ocr). Called by the material-text module as:
#     powershell -File <this script> -In picture.png -Out text.txt
#
# Nothing leaves this machine: no network, no extra install, no upload.
#
# THIS FILE MUST STAY PURE ASCII (bytes 0-127 only). PowerShell 5.1 decodes a .ps1
# without a BOM as ANSI, and on a Chinese Windows that means GBK -- where one CJK
# char takes 2 bytes instead of UTF-8's 3, so the leftover byte gets glued onto the
# NEXT character. If that character happens to be a quote, a hash or a newline, the
# script breaks or silently changes meaning. So: English comments and ASCII
# identifiers only. The material-format self-check measures this file's bytes and
# fails if any byte is above 127 -- do not rely on this comment alone.
#
# Out-File -Encoding utf8 writes a UTF-8 BOM under PowerShell 5.1, so the caller
# must read the output as utf-8-sig (it does).
#
# Exit codes: 0 ok; 2 no OCR engine or no language pack; 3 image too large for the
#             engine; 4 cannot open the image at all.
param(
    [Parameter(Mandatory = $true)][string]$In,
    [Parameter(Mandatory = $true)][string]$Out
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]

function Await($op, $resultType) {
    $task = $asTaskGeneric.MakeGenericMethod($resultType).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    $task.Result
}

# WinRT's GetFileFromPathAsync only accepts backslashes; a forward slash makes it
# throw a bare "One or more errors occurred", which tells the reader nothing.
$In = $In -replace '/', '\'
$Out = $Out -replace '/', '\'

# The engine splits a line into words. Chinese gets chopped per word, so joining
# with a space would insert spaces between Chinese words; English needs the space
# or a two-word line collapses into one run-on word. So: insert a space only when
# neither side is CJK. The test below covers Han, Han punctuation and fullwidth
# forms -- it does not cover kana or hangul, which this project has no use for.
function Join-Words($words) {
    $sb = New-Object System.Text.StringBuilder
    $prev = $null
    foreach ($w in $words) {
        $t = $w.Text
        if (-not $t) { continue }
        if ($null -ne $prev) {
            $leftIsCJK = $prev -match '[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]$'
            $rightIsCJK = $t -match '^[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]'
            if (-not ($leftIsCJK -or $rightIsCJK)) {
                [void]$sb.Append(' ')
            }
        }
        [void]$sb.Append($t)
        $prev = $t
    }
    $sb.ToString()
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null

$engine = $null
try {
    $lang = New-Object Windows.Globalization.Language 'zh-Hans-CN'
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
}
catch { }
if ($null -eq $engine) {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}
if ($null -eq $engine) {
    Write-Error 'no OCR engine available'
    exit 2
}

try {
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($In)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
}
catch {
    Write-Error ("cannot open this image: {0}" -f $_.Exception.Message)
    exit 4
}

# The engine throws on oversized images, so check first and let the caller retry smaller
if ($decoder.PixelWidth -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension -or
    $decoder.PixelHeight -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension) {
    Write-Error ("image too large for the OCR engine: {0}x{1}" -f $decoder.PixelWidth, $decoder.PixelHeight)
    exit 3
}

$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

# one output line per recognised line, joined by the rule above
$lines = foreach ($line in $result.Lines) {
    Join-Words $line.Words
}
$lines | Out-File -FilePath $Out -Encoding utf8
Write-Output ("lines={0} chars={1}" -f $lines.Count, ($lines -join '').Length)
