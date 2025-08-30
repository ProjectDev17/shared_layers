Listar versiones del layer:
aws lambda list-layer-versions --layer-name common-utils-py312 --query 'LayerVersions[].Version' --output text

Para borrar versiones antiguas manualmente:
aws lambda delete-layer-version --layer-name common-utils-py312 --version-number 15

Docker volume mounts para evitar rebuild innecesario
sam build --use-container
sam deploy