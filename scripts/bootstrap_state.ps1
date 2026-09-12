param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$BucketName = "procambrian-iris-staging-tfstate",

    [string]$Location = "asia-south1"
)

$ErrorActionPreference = "Stop"

gcloud config set project $ProjectId | Out-Null

$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$existing = gcloud storage buckets describe "gs://$BucketName" --project=$ProjectId 2>$null
$describeExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorAction

if ($describeExitCode -eq 0) {
    Write-Output "Using existing state bucket: gs://$BucketName"
} elseif ($describeExitCode -eq 1) {
    gcloud storage buckets create "gs://$BucketName" --project=$ProjectId --location=$Location --uniform-bucket-level-access --public-access-prevention
} else {
    throw "Could not determine whether the state bucket exists. Check gcloud authentication and permissions."
}

gcloud storage buckets update "gs://$BucketName" --versioning --uniform-bucket-level-access --public-access-prevention

Write-Output "Terraform state bucket is ready: gs://$BucketName"
Write-Output "Next command: terraform init -reconfigure -backend-config=\"bucket=$BucketName\""
