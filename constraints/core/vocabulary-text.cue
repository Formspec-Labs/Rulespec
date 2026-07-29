package rkaf

import (
	"list"
	"struct"
)

// One authoritative BCP 47 grammar for every authored language tag. The
// language-map carriers and ValueAssertion's JSON-LD language branch both
// reference this definition; no generated surface owns a second copy.
#BCP47LanguageTag: string & =~"^(?:(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}|[A-Za-z]{4}|[A-Za-z]{5,8})(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(?:-[0-9A-WY-Za-wy-z](?:-[A-Za-z0-9]{2,8})+)*(?:-[xX](?:-[A-Za-z0-9]{1,8})+)?|[xX](?:-[A-Za-z0-9]{1,8})+|[eE][nN]-[gG][bB]-[oO][eE][dD]|[iI]-(?:[aA][mM][iI]|[bB][nN][nN]|[dD][eE][fF][aA][uU][lL][tT]|[eE][nN][oO][cC][hH][iI][aA][nN]|[hH][aA][kK]|[kK][lL][iI][nN][gG][oO][nN]|[lL][uU][xX]|[mM][iI][nN][gG][oO]|[nN][aA][vV][aA][jJ][oO]|[pP][wW][nN]|[tT][aA][oO]|[tT][aA][yY]|[tT][sS][uU])|[sS][gG][nN]-(?:[bB][eE]-[fF][rR]|[bB][eE]-[nN][lL]|[cC][hH]-[dD][eE])|[aA][rR][tT]-[lL][oO][jJ][bB][aA][nN]|[cC][eE][lL]-[gG][aA][uU][lL][iI][sS][hH]|[nN][oO]-(?:[bB][oO][kK]|[nN][yY][nN])|[zZ][hH]-(?:[gG][uU][oO][yY][uU]|[hH][aA][kK][kK][aA]|[mM][iI][nN]|[mM][iI][nN]-[nN][aA][nN]|[xX][iI][aA][nN][gG]))$" & !~"^@none$"

#NonEmptyVocabularyText: string & =~"^[\\s\\S]+$"

// JSON-LD language maps preserve the authoring language and script. A
// preferred-label map admits one string per language. Other authored SKOS
// text admits one or many strings per language.
#PreferredLabelMap: struct.MinFields(1) & {
	[language=#BCP47LanguageTag]: #NonEmptyVocabularyText
}

#VocabularyTextMap: struct.MinFields(1) & {
	[language=#BCP47LanguageTag]: #NonEmptyVocabularyText |
		([...#NonEmptyVocabularyText] & list.MinItems(1))
}

// Closed JSON-LD typed-literal authoring object for skos:notation.
#NotationLiteral: {
	"@value": #NonEmptyVocabularyText
	"@type":  string & =~"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$"
}

#SkosAuthoredText: {
	"skos:prefLabel":      #PreferredLabelMap
	"skos:altLabel"?:      #VocabularyTextMap
	"skos:hiddenLabel"?:   #VocabularyTextMap
	"skos:definition"?:    #VocabularyTextMap
	"skos:example"?:       #VocabularyTextMap
	"skos:note"?:          #VocabularyTextMap
	"skos:scopeNote"?:     #VocabularyTextMap
	"skos:changeNote"?:    #VocabularyTextMap
	"skos:editorialNote"?: #VocabularyTextMap
	"skos:historyNote"?:   #VocabularyTextMap
}

#SkosConceptAuthoredText: {
	#SkosAuthoredText
	// Normative authoring form is a non-empty JSON array. The strict-list
	// marker tells semantic projections not to admit JSON-LD scalar shorthand;
	// RDF SHACL can validate the expanded literals but cannot recover whether
	// the compact source used an array, so source/JSON validation runs first.
	"skos:notation"?: [...#NotationLiteral] & list.MinItems(1) @rkafStrictList()
}
