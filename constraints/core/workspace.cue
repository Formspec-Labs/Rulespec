package rkaf

#Workspace: {
	"@type":                   "rkaf:Workspace"
	"rkaf:workspaceId":        string & =~"^[a-z0-9][a-z0-9-]+$"
	"rkaf:workspaceTrustList"?: [...string]
}
