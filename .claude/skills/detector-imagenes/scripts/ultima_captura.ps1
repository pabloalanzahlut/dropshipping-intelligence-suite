# Devuelve la ruta de la imagen más reciente en carpetas habituales de capturas.
$pics = [Environment]::GetFolderPath('MyPictures')
$dirs = @(
  (Join-Path $pics 'Screenshots'),
  (Join-Path $pics 'Capturas de pantalla'),
  (Join-Path $env:USERPROFILE 'OneDrive\Pictures\Screenshots'),
  [Environment]::GetFolderPath('Desktop'),
  (Join-Path $env:USERPROFILE 'Downloads')
) | Where-Object { $_ -and (Test-Path $_) }

Get-ChildItem -Path $dirs -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Extension -match '^\.(png|jpe?g|webp|gif|bmp)$' } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 -ExpandProperty FullName
