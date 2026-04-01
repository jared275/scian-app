from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unicodedata
from typing import Any, Dict, List

import pandas as pd
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from search_config import QUERY_EXPANSIONS, QUERY_INTENT_RULES, STOPWORDS, TITLE_HINT_RULES

LEVELS = ["sector", "subsector", "rama", "subrama"]
LEVEL_LABELS = {
    "sector": "Sector",
    "subsector": "Subsector",
    "rama": "Rama",
    "subrama": "Subrama",
}
LEVEL_WEIGHT_BY_PATH = {
    "sector": 0.90,
    "subsector": 0.95,
    "rama": 0.98,
    "subrama": 1.00,
}
TRAILING_T_EXCEPTIONS = {
    "internet",
    "chat",
    "resort",
    "outlet",
    "gourmet",
}


@dataclass(slots=True)
class CatalogNode:
    id: str
    level: str
    code: str
    title: str
    parent_id: str | None
    children_ids: List[str] = field(default_factory=list)
    search_text: str = ""
    normalized_search_text: str = ""
    breadcrumb: List[Dict[str, str]] = field(default_factory=list)
    descendant_path_ids: List[str] = field(default_factory=list)


@dataclass(slots=True)
class CatalogPath:
    id: str
    sector_id: str
    subsector_id: str
    rama_id: str
    subrama_id: str
    sector_code: str
    subsector_code: str
    rama_code: str
    subrama_code: str
    sector_title: str
    subsector_title: str
    rama_title: str
    subrama_title: str
    breadcrumb: List[Dict[str, str]]
    search_text: str
    normalized_search_text: str


class ScianSearchEngine:
    def __init__(self, catalog_csv_path: str | Path) -> None:
        self.catalog_csv_path = Path(catalog_csv_path)
        self.nodes: Dict[str, CatalogNode] = {}
        self.paths: List[CatalogPath] = []
        self.nodes_by_level: Dict[str, List[CatalogNode]] = {level: [] for level in LEVELS}
        self.meta: Dict[str, Any] = {}
        self._load_catalog()
        self._build_indexes()

    @staticmethod
    def normalize_code(value: Any) -> str:
        text = str(value or "").strip()
        if text.endswith(".0"):
            text = text[:-2]
        return text

    @staticmethod
    def _ascii_token(text: str) -> str:
        value = unicodedata.normalize("NFD", text or "")
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        return value.lower()

    @classmethod
    def _clean_word(cls, token: str) -> str:
        if not token:
            return token

        match = re.match(r"^(\W*)(.*?)(\W*)$", token, flags=re.UNICODE)
        if not match:
            return token

        prefix, core, suffix = match.groups()
        if not core:
            return token

        normalized_core = cls._ascii_token(core)
        if len(normalized_core) > 4 and normalized_core.endswith("t") and normalized_core not in TRAILING_T_EXCEPTIONS:
            core = core[:-1]
        return f"{prefix}{core}{suffix}"

    @classmethod
    def clean_display_text(cls, text: str) -> str:
        value = re.sub(r"\s+", " ", (text or "").strip().strip('"'))
        if not value:
            return value
        return " ".join(cls._clean_word(token) for token in value.split(" ")).strip()

    @staticmethod
    def normalize_text(text: str) -> str:
        value = ScianSearchEngine.clean_display_text(text).lower()
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        value = value.replace("&", " y ")
        value = re.sub(r"[^a-z0-9]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def simplify_token(token: str) -> str:
        if len(token) > 5 and token.endswith("iones"):
            return token[:-2]
        if len(token) > 4 and token.endswith(("ales", "iles", "oles", "ules")):
            return token[:-2]
        if len(token) > 3 and token.endswith("s"):
            return token[:-1]
        return token

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        tokens: List[str] = []
        for token in cls.normalize_text(text).split():
            if token in STOPWORDS:
                continue
            tokens.append(cls.simplify_token(token))
        return tokens

    @classmethod
    def expand_query(cls, query: str) -> str:
        raw_tokens = set(cls.normalize_text(query).split())
        simplified_tokens = set(cls.tokenize(query))
        tokens = raw_tokens | simplified_tokens

        extra_terms: List[str] = []
        seen_expansions: set[str] = set()
        for token in tokens:
            expansion = QUERY_EXPANSIONS.get(token)
            if expansion and expansion not in seen_expansions:
                extra_terms.append(expansion)
                seen_expansions.add(expansion)

        expanded = f"{query} {' '.join(extra_terms)}".strip()
        return re.sub(r"\s+", " ", expanded)

    @classmethod
    def enrich_catalog_text(cls, text: str) -> str:
        normalized = cls.normalize_text(text)
        extra_terms: List[str] = []
        for pattern, hints in TITLE_HINT_RULES:
            if re.search(pattern, normalized):
                extra_terms.append(hints)
        enriched = f"{text} {' '.join(extra_terms)}".strip()
        return re.sub(r"\s+", " ", enriched)

    @classmethod
    def intent_adjustment(cls, raw_query: str, normalized_candidate_text: str) -> float:
        query_tokens = set(cls.normalize_text(raw_query).split()) | set(cls.tokenize(raw_query))
        adjustment = 0.0
        for rule in QUERY_INTENT_RULES:
            if not query_tokens.intersection(rule["triggers"]):
                continue
            if any(re.search(pattern, normalized_candidate_text) for pattern in rule.get("positive_patterns", [])):
                adjustment += float(rule.get("positive_boost", 0.0))
            if any(re.search(pattern, normalized_candidate_text) for pattern in rule.get("negative_patterns", [])):
                adjustment -= float(rule.get("negative_penalty", 0.0))
        return adjustment

    @staticmethod
    def score_to_percent(score: float) -> float:
        bounded = max(0.0, min(score, 1.0))
        return round(bounded * 100, 1)

    @staticmethod
    def breadcrumb_to_copy_text(breadcrumb: List[Dict[str, str]]) -> str:
        return " > ".join(
            f"{piece['level_label']} {piece['code']} - {piece['title']}" for piece in breadcrumb
        )

    @staticmethod
    def guide_score_for_node(level: str, direct_score: float, descendant_score: float) -> float:
        if level == "subrama":
            return max(direct_score, descendant_score)
        return max(descendant_score, direct_score * 0.96)

    def _load_catalog(self) -> None:
        dataframe = pd.read_csv(self.catalog_csv_path, dtype=str).fillna("")
        dataframe = dataframe[dataframe["codigo_subrama"].astype(str).str.strip() != ""].copy()

        for _, row in dataframe.iterrows():
            sector_code = self.normalize_code(row["codigo_sector"])
            subsector_code = self.normalize_code(row["codigo_subsector"])
            rama_code = self.normalize_code(row["codigo_rama"])
            subrama_code = self.normalize_code(row["codigo_subrama"])

            sector_title = self.clean_display_text(row["nombre_sector"])
            subsector_title = self.clean_display_text(row["nombre_subsector"])
            rama_title = self.clean_display_text(row["nombre_rama"])
            subrama_title = self.clean_display_text(row["nombre_subrama"])

            sector_id = f"sector:{sector_code}"
            subsector_id = f"subsector:{subsector_code}"
            rama_id = f"rama:{rama_code}"
            subrama_id = f"subrama:{subrama_code}"

            node_specs = [
                (sector_id, "sector", sector_code, sector_title, None),
                (subsector_id, "subsector", subsector_code, subsector_title, sector_id),
                (rama_id, "rama", rama_code, rama_title, subsector_id),
                (subrama_id, "subrama", subrama_code, subrama_title, rama_id),
            ]

            breadcrumb: List[Dict[str, str]] = []
            for node_id, level, code, title, parent_id in node_specs:
                if node_id not in self.nodes:
                    self.nodes[node_id] = CatalogNode(
                        id=node_id,
                        level=level,
                        code=code,
                        title=title,
                        parent_id=parent_id,
                    )
                    if parent_id and node_id not in self.nodes[parent_id].children_ids:
                        self.nodes[parent_id].children_ids.append(node_id)

                breadcrumb.append(
                    {
                        "id": node_id,
                        "level": level,
                        "level_label": LEVEL_LABELS[level],
                        "code": code,
                        "title": title,
                    }
                )

            search_text = self.enrich_catalog_text(
                " > ".join([sector_title, subsector_title, rama_title, subrama_title])
            )
            normalized_search_text = self.normalize_text(search_text)

            self.paths.append(
                CatalogPath(
                    id=f"path:{subrama_code}",
                    sector_id=sector_id,
                    subsector_id=subsector_id,
                    rama_id=rama_id,
                    subrama_id=subrama_id,
                    sector_code=sector_code,
                    subsector_code=subsector_code,
                    rama_code=rama_code,
                    subrama_code=subrama_code,
                    sector_title=sector_title,
                    subsector_title=subsector_title,
                    rama_title=rama_title,
                    subrama_title=subrama_title,
                    breadcrumb=breadcrumb,
                    search_text=search_text,
                    normalized_search_text=normalized_search_text,
                )
            )

        for node in self.nodes.values():
            node.breadcrumb = self._build_breadcrumb(node.id)
            node.search_text = self.enrich_catalog_text(" > ".join(part["title"] for part in node.breadcrumb))
            node.normalized_search_text = self.normalize_text(node.search_text)

        for path in self.paths:
            for node_id in [path.sector_id, path.subsector_id, path.rama_id, path.subrama_id]:
                self.nodes[node_id].descendant_path_ids.append(path.id)

        for level in LEVELS:
            self.nodes_by_level[level] = sorted(
                [node for node in self.nodes.values() if node.level == level],
                key=lambda node: int(node.code) if node.code.isdigit() else node.code,
            )

        self.meta = {
            "rows": len(self.paths),
            "levels": {level: len(self.nodes_by_level[level]) for level in LEVELS},
        }

    def _build_breadcrumb(self, node_id: str) -> List[Dict[str, str]]:
        pieces: List[Dict[str, str]] = []
        current_id = node_id
        while current_id:
            node = self.nodes[current_id]
            pieces.append(
                {
                    "id": node.id,
                    "level": node.level,
                    "level_label": LEVEL_LABELS[node.level],
                    "code": node.code,
                    "title": node.title,
                }
            )
            current_id = node.parent_id or ""
        return list(reversed(pieces))

    def _build_indexes(self) -> None:
        combined_documents = [path.search_text for path in self.paths] + [
            node.search_text for node in self.nodes.values()
        ]
        normalized_documents = [self.normalize_text(text) for text in combined_documents]

        self.word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 3), min_df=1)
        self.char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)

        self.word_vectorizer.fit(normalized_documents)
        self.char_vectorizer.fit(normalized_documents)

        self.path_word_matrix = self.word_vectorizer.transform(
            [path.normalized_search_text for path in self.paths]
        )
        self.path_char_matrix = self.char_vectorizer.transform(
            [path.normalized_search_text for path in self.paths]
        )

        self.node_list = list(self.nodes.values())
        self.node_word_matrix = self.word_vectorizer.transform(
            [node.normalized_search_text for node in self.node_list]
        )
        self.node_char_matrix = self.char_vectorizer.transform(
            [node.normalized_search_text for node in self.node_list]
        )

    def _search_nodes(self, raw_query: str, expanded_query: str) -> List[float]:
        normalized_query = self.normalize_text(expanded_query)
        normalized_raw_query = self.normalize_text(raw_query)
        query_word = self.word_vectorizer.transform([normalized_query])
        query_char = self.char_vectorizer.transform([normalized_query])

        word_scores = cosine_similarity(query_word, self.node_word_matrix).ravel()
        char_scores = cosine_similarity(query_char, self.node_char_matrix).ravel()

        scores: List[float] = []
        for idx, node in enumerate(self.node_list):
            fuzzy_score = fuzz.token_set_ratio(normalized_raw_query, node.normalized_search_text) / 100.0
            exact_bonus = 0.06 if normalized_raw_query and normalized_raw_query in node.normalized_search_text else 0.0
            intent_bonus = self.intent_adjustment(raw_query, node.normalized_search_text)
            score = (
                (0.68 * float(word_scores[idx]))
                + (0.18 * float(char_scores[idx]))
                + (0.14 * fuzzy_score)
                + exact_bonus
                + intent_bonus
            )
            scores.append(score)
        return scores

    def _search_paths(self, raw_query: str, expanded_query: str, node_score_by_id: Dict[str, float]) -> List[float]:
        normalized_query = self.normalize_text(expanded_query)
        normalized_raw_query = self.normalize_text(raw_query)
        query_word = self.word_vectorizer.transform([normalized_query])
        query_char = self.char_vectorizer.transform([normalized_query])

        word_scores = cosine_similarity(query_word, self.path_word_matrix).ravel()
        char_scores = cosine_similarity(query_char, self.path_char_matrix).ravel()

        scores: List[float] = []
        for idx, path in enumerate(self.paths):
            fuzzy_score = fuzz.token_set_ratio(normalized_raw_query, path.normalized_search_text) / 100.0
            exact_bonus = 0.05 if normalized_raw_query and normalized_raw_query in path.normalized_search_text else 0.0
            intent_bonus = self.intent_adjustment(raw_query, path.normalized_search_text)
            direct_score = (
                (0.62 * float(word_scores[idx]))
                + (0.20 * float(char_scores[idx]))
                + (0.18 * fuzzy_score)
                + exact_bonus
                + intent_bonus
            )

            sector_score = node_score_by_id[path.sector_id]
            subsector_score = node_score_by_id[path.subsector_id]
            rama_score = node_score_by_id[path.rama_id]
            subrama_score = node_score_by_id[path.subrama_id]

            hierarchy_score = (
                0.06 * sector_score
                + 0.14 * subsector_score
                + 0.28 * rama_score
                + 0.52 * subrama_score
            )
            promoted_score = max(
                sector_score * LEVEL_WEIGHT_BY_PATH["sector"],
                subsector_score * LEVEL_WEIGHT_BY_PATH["subsector"],
                rama_score * LEVEL_WEIGHT_BY_PATH["rama"],
                subrama_score * LEVEL_WEIGHT_BY_PATH["subrama"],
            )

            scores.append(max(direct_score, hierarchy_score, promoted_score))
        return scores

    def _compute_descendant_scores(self, path_score_by_id: Dict[str, float]) -> Dict[str, float]:
        descendant_scores: Dict[str, float] = {}
        for node in self.node_list:
            max_score = 0.0
            for path_id in node.descendant_path_ids:
                max_score = max(max_score, path_score_by_id[path_id])
            descendant_scores[node.id] = max_score
        return descendant_scores

    def _serialize_path(
        self,
        path: CatalogPath,
        score: float,
        node_score_by_id: Dict[str, float],
    ) -> Dict[str, Any]:
        level_scores = {
            "sector": node_score_by_id[path.sector_id],
            "subsector": node_score_by_id[path.subsector_id],
            "rama": node_score_by_id[path.rama_id],
            "subrama": node_score_by_id[path.subrama_id],
        }
        best_level = max(level_scores, key=level_scores.get)
        copy_text = self.breadcrumb_to_copy_text(path.breadcrumb)
        return {
            "id": path.id,
            "score": round(score, 4),
            "score_pct": self.score_to_percent(score),
            "best_level": best_level,
            "best_level_label": LEVEL_LABELS[best_level],
            "breadcrumb": path.breadcrumb,
            "copy_text": copy_text,
            "levels": {
                "sector": {
                    "id": path.sector_id,
                    "code": path.sector_code,
                    "title": path.sector_title,
                    "score": round(level_scores["sector"], 4),
                    "score_pct": self.score_to_percent(level_scores["sector"]),
                },
                "subsector": {
                    "id": path.subsector_id,
                    "code": path.subsector_code,
                    "title": path.subsector_title,
                    "score": round(level_scores["subsector"], 4),
                    "score_pct": self.score_to_percent(level_scores["subsector"]),
                },
                "rama": {
                    "id": path.rama_id,
                    "code": path.rama_code,
                    "title": path.rama_title,
                    "score": round(level_scores["rama"], 4),
                    "score_pct": self.score_to_percent(level_scores["rama"]),
                },
                "subrama": {
                    "id": path.subrama_id,
                    "code": path.subrama_code,
                    "title": path.subrama_title,
                    "score": round(level_scores["subrama"], 4),
                    "score_pct": self.score_to_percent(level_scores["subrama"]),
                },
            },
        }

    def _serialize_node(
        self,
        node: CatalogNode,
        direct_score: float,
        descendant_max_score: float,
        child_ids: List[str],
    ) -> Dict[str, Any]:
        guide_score = self.guide_score_for_node(node.level, direct_score, descendant_max_score)
        copy_text = self.breadcrumb_to_copy_text(node.breadcrumb)
        return {
            "id": node.id,
            "level": node.level,
            "level_label": LEVEL_LABELS[node.level],
            "code": node.code,
            "title": node.title,
            "score": round(direct_score, 4),
            "score_pct": self.score_to_percent(direct_score),
            "descendant_max_score": round(descendant_max_score, 4),
            "descendant_max_score_pct": self.score_to_percent(descendant_max_score),
            "guide_score": round(guide_score, 4),
            "guide_score_pct": self.score_to_percent(guide_score),
            "breadcrumb": node.breadcrumb,
            "copy_text": copy_text,
            "parent_id": node.parent_id,
            "child_ids": child_ids,
            "children_count": len(node.children_ids),
            "path_count": len(node.descendant_path_ids),
        }

    def search(self, query: str, top_n: int = 12) -> Dict[str, Any]:
        raw_query = (query or "").strip()
        if not raw_query:
            return {
                "query": "",
                "expanded_query": "",
                "meta": self.meta,
                "top_paths": [],
                "guide": {
                    "root_sector_ids": [],
                    "default_selection": {f"{level}_id": None for level in LEVELS},
                    "nodes": {},
                    "best_path": None,
                },
            }

        expanded_query = self.expand_query(raw_query)
        node_scores = self._search_nodes(raw_query, expanded_query)
        node_score_by_id = {node.id: node_scores[idx] for idx, node in enumerate(self.node_list)}

        path_scores = self._search_paths(raw_query, expanded_query, node_score_by_id)
        path_score_by_id = {path.id: path_scores[idx] for idx, path in enumerate(self.paths)}
        descendant_scores = self._compute_descendant_scores(path_score_by_id)

        top_paths = sorted(
            [
                self._serialize_path(path, path_score_by_id[path.id], node_score_by_id)
                for path in self.paths
            ],
            key=lambda item: item["score"],
            reverse=True,
        )[:top_n]

        ordered_children_by_id: Dict[str, List[str]] = {}
        for node in self.node_list:
            ordered_children_by_id[node.id] = sorted(
                node.children_ids,
                key=lambda child_id: (
                    self.guide_score_for_node(
                        self.nodes[child_id].level,
                        node_score_by_id[child_id],
                        descendant_scores[child_id],
                    ),
                    node_score_by_id[child_id],
                ),
                reverse=True,
            )

        explorer_nodes = {
            node.id: self._serialize_node(
                node=node,
                direct_score=node_score_by_id[node.id],
                descendant_max_score=descendant_scores[node.id],
                child_ids=ordered_children_by_id[node.id],
            )
            for node in self.node_list
        }

        top_sector_ids = [
            node.id
            for node in sorted(
                self.nodes_by_level["sector"],
                key=lambda node: (
                    self.guide_score_for_node(
                        node.level,
                        node_score_by_id[node.id],
                        descendant_scores[node.id],
                    ),
                    node_score_by_id[node.id],
                ),
                reverse=True,
            )[:6]
        ]

        default_selection = {f"{level}_id": None for level in LEVELS}
        if top_paths:
            best_path = top_paths[0]
            for level in LEVELS:
                default_selection[f"{level}_id"] = best_path["levels"][level]["id"]
        else:
            best_path = None

        return {
            "query": raw_query,
            "expanded_query": expanded_query,
            "meta": self.meta,
            "top_paths": top_paths,
            "guide": {
                "root_sector_ids": top_sector_ids,
                "default_selection": default_selection,
                "nodes": explorer_nodes,
                "best_path": best_path,
            },
        }
