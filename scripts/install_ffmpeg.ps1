$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$tools = Join-Path $project '.tools'
$target = Join-Path $tools 'ffmpeg'
$archive = Join-Path $tools 'ffmpeg.zip'
$checksum = Join-Path $tools 'ffmpeg.sha256'
$extract = Join-Path $tools ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $tools, $target | Out-Null

try {
    if (-not (Test-Path -LiteralPath $checksum)) {
        Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256' -OutFile $checksum
    }
    if (-not (Test-Path -LiteralPath $archive)) {
        Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $archive
    }
    $expected = (Get-Content -LiteralPath $checksum -Raw).Trim()
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    if ($actual -ine $expected) { throw 'Checksum SHA256 do FFmpeg não confere.' }
    Expand-Archive -LiteralPath $archive -DestinationPath $extract
    $binary = Get-ChildItem -LiteralPath $extract -Filter 'ffmpeg.exe' -File -Recurse | Select-Object -First 1
    if (-not $binary) { throw 'ffmpeg.exe não encontrado no pacote.' }
    $probe = Join-Path $binary.DirectoryName 'ffprobe.exe'
    if (-not (Test-Path -LiteralPath $probe)) { throw 'ffprobe.exe não encontrado no pacote.' }
    Copy-Item -LiteralPath $binary.FullName -Destination (Join-Path $target 'ffmpeg.exe')
    Copy-Item -LiteralPath $probe -Destination (Join-Path $target 'ffprobe.exe')
    & (Join-Path $target 'ffmpeg.exe') -version | Select-Object -First 1
    & (Join-Path $target 'ffprobe.exe') -version | Select-Object -First 1
} finally {
    $resolvedTools = [IO.Path]::GetFullPath($tools).TrimEnd('\') + '\'
    $resolvedExtract = [IO.Path]::GetFullPath($extract)
    if ($resolvedExtract.StartsWith($resolvedTools, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $archive, $checksum -Force -ErrorAction SilentlyContinue
}
