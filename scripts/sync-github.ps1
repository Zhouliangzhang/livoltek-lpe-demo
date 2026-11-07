$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$account = gh api user --jq .login
if ($LASTEXITCODE -ne 0) { throw 'Please run gh auth login -h github.com first.' }
if ($account.Trim() -ne 'Zhouliangzhang') { throw 'Expected GitHub account Zhouliangzhang. No repository was created.' }
$remote = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    if ($remote -ne 'https://github.com/Zhouliangzhang/livoltek-lpe-demo.git') { throw 'Unexpected origin. Review manually.' }
    $private = gh repo view Zhouliangzhang/livoltek-lpe-demo --json isPrivate --jq .isPrivate
    if ($LASTEXITCODE -ne 0) { throw 'Cannot verify remote repository.' }
    if ($private.Trim() -ne 'true') { throw 'Remote is not private. Review manually before uploading baseline documents.' }
    git push -u origin main
} else {
    gh repo view Zhouliangzhang/livoltek-lpe-demo --json name 2>$null
    if ($LASTEXITCODE -eq 0) { throw 'Repository already exists. Review before attaching this local project.' }
    gh repo create Zhouliangzhang/livoltek-lpe-demo --private --source . --remote origin --push --description 'LIVOLTEK Project Engineer M1 and M2 operational demo'
}
if ($LASTEXITCODE -ne 0) { throw 'GitHub sync failed. Local work is preserved.' }
git show-ref --verify --quiet refs/heads/develop
if ($LASTEXITCODE -ne 0) { git branch develop }
git push -u origin develop
if ($LASTEXITCODE -ne 0) { throw 'Develop branch sync failed.' }
Write-Host 'Remote sync completed. Use git switch develop for development.'
