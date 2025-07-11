from pathlib import Path
from typing import Dict, Any, List, Tuple, Iterable
import random

try:
    import numpy as np
    from rtree import index
    from tqdm import tqdm
except ImportError:
    raise ImportError("Install numpy, rtree, and tqdm: `pip install logngine[dev]`")

from .SVUVParser import SVUVParser
from .SourceWriter import SourceFile, SourceObject

class DatasetBaker:
    ROOT = Path(__file__).parent.parent.resolve()
    IN_PATH = ROOT / 'datasets' / 'data'
    OUT_PATH = ROOT / 'src' / 'cpp' / 'include' / 'logngine' / 'data'
    CSV_PATH = ROOT / 'src' / 'logngine' / 'data'
    CITATION_FILE = OUT_PATH / 'Citations.h'

    citations: list[str] = []

    def __init__(self):
        self.parser = SVUVParser()
        self.dataset = {}

        self.table_name = ""
        self.data_name = ""
        self.entry_name = ""
        self.make_function_name = ""

        for path in self.IN_PATH.rglob("*.svuv"):
            out_path = self.OUT_PATH / path.relative_to(self.IN_PATH)
            csv_path = self.CSV_PATH / path.relative_to(self.IN_PATH)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            self.parser.read(path)  # pre-read for parsing's sake; kinda wasteful but who cares

        for path in self.IN_PATH.rglob("*.svuv"):
            out_path = self.OUT_PATH / path.relative_to(self.IN_PATH)
            csv_path = self.CSV_PATH / path.relative_to(self.IN_PATH)
            header_name = ''.join(w.capitalize() for w in path.stem.split('-')) + ".h"
            namespace = "::".join(path.relative_to(self.IN_PATH).parts[:-1])
            namespace = f"logngine::data::{namespace}" if namespace else "logngine::data"

            self.compile_to_header(path, out_path.with_name(header_name), namespace)
            self.compile_to_csv(csv_path.with_name(str(Path(header_name).stem + '.csv')))
        self.compile_citations()

    def compile_to_csv(self, out_path: Path, *, include_uncert=True, include_cite=True) -> None:
        self.parser.to_csv(out_path, include_uncert=include_uncert, include_cite=include_cite)

    def compile_to_header(self, in_path: Path, out_path: Path, namespace: str):
        self.dataset = self.parser.read(in_path)
        self._collect_citations()

        order = self._optimize_ordering()
        self._apply_order(order)

        self.table_name = out_path.stem
        self.make_function_name = f'_make_baked_{self.table_name.lower()}_dataset'
        self.data_name = f'{self.table_name}Data'
        self.entry_name = f'{self.table_name}Entry'

        writer = SourceFile(namespace)
        writer.add_include("array")
        writer.add_include("logngine/core/RSTTree.h")

        headers = [k for k in self.dataset if '$' not in k]
        n_features = len(headers)

        data_struct = SourceObject.Struct(self.data_name, **{k: "const double" for k in headers})
        table_struct = SourceObject.Struct(self.entry_name, data=f"const {self.data_name}", uncertainty=f"const {self.data_name}", citation="const unsigned int")

        writer.add(data_struct)
        writer.add(table_struct)

        inserts = self._generate_insert_statements(headers)
        inserts.insert(0, f"logngine::core::RSTTree<{self.entry_name}, {n_features}, 16, 16> {self.table_name}{{}};")
        inserts.append(f"return {self.table_name};")

        factory = SourceObject.Function(
            self.make_function_name,
            inserts,
            f"inline logngine::core::RSTTree<{self.entry_name}, {n_features}, 16, 16>"
        )
        writer.add(factory)

        result = SourceObject.Variable(
            f"const logngine::core::RSTTree<{self.entry_name}, {n_features}, 16, 16>",
            self.table_name,
            f"{self.make_function_name}()"
        )
        writer.add(result)
        writer.build()

        with open(out_path, "w", encoding="utf-8") as f:
            self._watermark(f)
            f.write(writer.get_output())

    def _collect_citations(self):
        for citation in self.dataset["$citation"]:
            if citation not in self.__class__.citations:
                self.__class__.citations.append(citation)

    def compile_citations(self):
        writer = SourceFile(namespace="logngine::data")
        writer.add_include("cstddef")

        initializer_lines = [
            f'"{entry}"' for entry in self.citations
        ]

        citation_array = SourceObject.Variable(
            type_="constexpr const char*[]",
            name="CITATIONS",
            init=initializer_lines
        )

        count_var = SourceObject.Variable(
            type_="constexpr std::size_t",
            name="NUM_CITATIONS",
            init=str(len(self.citations))
        )

        writer.add(citation_array)
        writer.add(count_var)

        writer.build()
        self.CITATION_FILE.parent.mkdir(parents=True, exist_ok=True)

        with self.CITATION_FILE.open("w+", encoding="utf-8") as f:
            self._watermark(f)
            f.write(writer.get_output())

    @staticmethod
    def _watermark(f):
        f.write('// Automatically generated by (project-root)/tools/DatasetBaker.py\n\n')

    def _optimize_ordering(self) -> List[int]:
        ordered, _ = self._find_best_insertion_order(self._dataset_to_rtree_entries(self.dataset))
        return [int(label) for _, label in ordered]

    def _apply_order(self, order: List[int]):
        self.dataset = {k: [self.dataset[k][i] for i in order] for k in self.dataset}

    def _generate_insert_statements(self, headers: list[str]) -> list[str]:
        keys = self._generate_key_initializers(headers)
        values = self._generate_entry_initializers(headers)
        return [f"{self.table_name}.insert({k}, {v});" for k, v in zip(keys, values)]

    def _generate_key_initializers(self, headers: list[str]) -> list[str]:
        return [
            self._as_initializer(f"std::array<double, {len(headers)}>", map(str, row))
            for row in zip(*[self.dataset[h] for h in headers])
        ]

    def _generate_entry_initializers(self, headers: list[str]) -> list[str]:
        entries = []
        for data_row, uncert_row, citation in zip(
                zip(*[self.dataset[h] for h in headers]),
                zip(*[self.dataset[h + "$uncertainty"] for h in headers]),
                self.dataset["$citation"]
        ):
            d = self._as_initializer(self.data_name, map(str, data_row))
            u = self._as_initializer(self.data_name, map(str, uncert_row))
            c = str(self.__class__.citations.index(citation))
            entries.append(self._as_initializer(self.entry_name, [d, u, c]))
        return entries

    @staticmethod
    def _as_initializer(name: str, fields: Iterable[str]) -> str:
        return f"{name}{{{', '.join(fields)}}}"

    @staticmethod
    def _dataset_to_rtree_entries(data: Dict[str, List[Any]]) -> List[Tuple[Tuple[List[float], List[float]], str]]:
        headers = [k for k in data if '$' not in k]
        zipped = list(zip(*[data[h] for h in headers]))
        return [((list(row), list(row)), str(i)) for i, row in enumerate(zipped)]

    @staticmethod
    def _mbr_volume(bounds: List[float]) -> float:
        d = len(bounds) // 2
        return np.prod([bounds[d+i] - bounds[i] for i in range(d)])

    @classmethod
    def _compute_overlap(cls, tree: index.Index) -> float:
        overlap = 0.0
        for i in tree.intersection(tree.bounds, objects=True):
            for j in tree.intersection(i.bbox, objects=True):
                if i.id >= j.id:
                    continue
                dims = len(i.bbox) // 2
                inter = [max(i.bbox[k], j.bbox[k]) for k in range(dims)] +                         [min(i.bbox[k + dims], j.bbox[k + dims]) for k in range(dims)]
                if all(inter[k] < inter[k + dims] for k in range(dims)):
                    overlap += cls._mbr_volume(inter)
        return overlap

    @classmethod
    def _evaluate_tree(cls, entries: List[Tuple[Tuple[List[float], List[float]], str]]) -> Tuple[float, float]:
        p = index.Property()
        p.dimension = len(entries[0][0][0])
        tree = index.Index(properties=p)

        for i, ((lo, hi), _) in enumerate(entries):
            bbox = tuple(lo + hi)
            tree.insert(i, bbox)

        area = sum(cls._mbr_volume(obj.bbox) for obj in tree.intersection(tree.bounds, objects=True))
        overlap = cls._compute_overlap(tree)
        return area, overlap

    @classmethod
    def _find_best_insertion_order(cls, entries: List[Tuple[Tuple[List[float], List[float]], str]], trials: int = 1000):
        best, best_score, all_scores = [], float("inf"), []

        for _ in tqdm(range(trials), desc="Optimizing insertion order"):
            random.shuffle(entries)
            area, overlap = cls._evaluate_tree(entries)
            score = area + overlap
            all_scores.append((score, list(entries)))
            if score < best_score:
                best_score = score
                best = list(entries)

        return best, all_scores
