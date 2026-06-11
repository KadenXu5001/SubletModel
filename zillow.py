import kagglehub

# Download latest version
path = kagglehub.dataset_download("promptcloud/zillow-property-data-listing")

print("Path to dataset files:", path)