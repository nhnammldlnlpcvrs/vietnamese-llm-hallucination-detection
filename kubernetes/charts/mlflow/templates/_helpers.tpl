{{- define "mlflow.name" -}}
mlflow
{{- end }}

{{- define "mlflow.fullname" -}}
mlflow
{{- end }}

{{- define "mlflow.labels" -}}
app.kubernetes.io/name: mlflow
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: Helm
{{- end -}}
