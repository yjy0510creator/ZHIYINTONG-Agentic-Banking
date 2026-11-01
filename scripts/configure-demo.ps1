$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$envPath=Join-Path $root 'backend/.env'
if(Test-Path -LiteralPath $envPath){throw 'Refusing to overwrite existing backend/.env'}
function New-LocalSecret { $bytes=New-Object byte[] 32; $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); $rng.GetBytes($bytes);$rng.Dispose();[Convert]::ToBase64String($bytes) }
$template=[IO.File]::ReadAllText((Join-Path $root 'backend/.env.example'))
$template=$template.Replace('APP_ENV=production','APP_ENV=development').Replace('DEV_MAKER_PASSWORD=',('DEV_MAKER_PASSWORD='+(New-LocalSecret))).Replace('DEV_CHECKER_PASSWORD=',('DEV_CHECKER_PASSWORD='+(New-LocalSecret))).Replace('DEV_CUSTOMER2_PASSWORD=',('DEV_CUSTOMER2_PASSWORD='+(New-LocalSecret))).Replace('CORS_ORIGINS=http://localhost:3000','CORS_ORIGINS=http://localhost:3088')
$db=(Join-Path $root 'backend/data/demo.db').Replace('\','/')
$template+="`nBANKING_DB_PATH=$db`n"
[IO.File]::WriteAllText($envPath,$template)
$front=Join-Path $root 'frontend/.env.local'
if(!(Test-Path -LiteralPath $front)){[IO.File]::WriteAllText($front,'NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8088')}
Write-Output 'Independent development configuration created. Read credentials locally; do not publish .env.'
