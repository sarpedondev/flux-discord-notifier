{{- define "flux-discord-notifier.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "flux-discord-notifier.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "flux-discord-notifier.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "flux-discord-notifier.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "flux-discord-notifier.selectorLabels" -}}
app.kubernetes.io/name: {{ include "flux-discord-notifier.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "flux-discord-notifier.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "flux-discord-notifier.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "flux-discord-notifier.secretName" -}}
{{- default (include "flux-discord-notifier.fullname" .) .Values.secrets.existingSecret }}
{{- end }}

{{- define "flux-discord-notifier.providerName" -}}
{{- default (include "flux-discord-notifier.fullname" .) .Values.flux.providerName }}
{{- end }}

