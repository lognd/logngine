from pathlib import Path
from typing import Dict, Any, List, Tuple
import random

try:
    import numpy as np
    from rtree import index
    from tqdm import tqdm
except ImportError:
    raise ImportError("Install numpy, rtree, and tqdm (current `pip install logngine[dev]` is busted...) to use SourceBaker: `pip install logngine[dev]`")

from .SVUVParser import SVUVParser
from .SourceWriter import SourceContainer, SourceObject

class SourceBaker:

    PROJECT_ROOT: Path = Path(__file__).parent.parent.resolve()

    IN_DATA_PATH: Path = PROJECT_ROOT / 'datasets' / 'data'
    OUT_DATA_PATH: Path = PROJECT_ROOT / 'src' / 'cpp' / 'include' / 'logngine' / 'data'
    CITATION_PATH: Path = OUT_DATA_PATH / 'Citations.h'
    citations: list[str] = []
    table_name: str = 'table'

    def __init__(self):
        self.parser = SVUVParser()
        self.data = {}
        for path in self.IN_DATA_PATH.rglob("*.svuv"):
            new_path = self.OUT_DATA_PATH / path.relative_to(self.IN_DATA_PATH)
            new_directory = new_path.parent
            new_directory.mkdir(parents=True, exist_ok=True)
            file = new_path.stem
            new_file = ''.join([w.capitalize() for w in file.split('-')]) + '.h'

            namespace = '::'.join(path.relative_to(self.IN_DATA_PATH).parts[:-1])
            namespace = 'logngine::data::' + namespace if namespace else 'logngine::data'
            self.write_data_to_file(path, new_directory / new_file, namespace)

    def add_citations(self):
        for citation in self.data['$citation']:
            if citation not in self.__class__.citations: self.__class__.citations.append(citation)

    def shuffle_data_to_best_order(self, ordering: List[int]) -> Dict[str, List[Any]]:
        data_out = {k: [] for k in self.data}
        for key in data_out:
            data_out[key] = [self.data[key][i] for i in ordering]
        self.data = data_out
        return data_out

    def get_best_insertion_order(self) -> List[int]:
        best_ordered, _ = self.find_best_order(self.convert_to_dataset(self.data))
        return [int(label) for _, label in best_ordered]

    def write_data_to_file(self, in_file: str | Path, out_file: str | Path, namespace: str):
        self.data = self.parser.read(in_file)
        self.add_citations()

        best_order = self.get_best_insertion_order()
        self.shuffle_data_to_best_order(best_order)
        self.table_name = Path(out_file).stem

        writer = SourceContainer(namespace)
        writer.add_include('array')
        writer.add_include('logngine/core/RSTTree.h')
        bald_headers = [hdr for hdr in self.data if '$' not in hdr]

        data_holder = SourceObject.Struct('Data', **{hdr: 'const double' for hdr in bald_headers})
        table_entry = SourceObject.Struct('TableEntry', data='const Data', uncertainty='const Data', citation='const unsigned int')
        writer.add_object(data_holder)
        writer.add_object(table_entry)

        make_dataset_source = self.generate_inserts()
        make_dataset_source.insert(0, f"logngine::core::RSTTree<TableEntry, {len(bald_headers)}, 16, 16> {self.table_name}{{}};")
        make_dataset_source.append(f"return {self.table_name};")
        dataset_maker = SourceObject.Function(
            'make_dataset',
            make_dataset_source,
            f'inline logngine::core::RSTTree<TableEntry, {len(bald_headers)}, 16, 16>'
        )

        writer.add_object(dataset_maker)
        dataset = SourceObject.Variable(f'const logngine::core::RSTTree<TableEntry, {len(bald_headers)}, 16, 16>', self.table_name, 'make_dataset()')
        writer.add_object(dataset)

        writer.build_content()
        with open(str(out_file), 'w+') as f:
            f.write(writer.get_content())

    def generate_inserts(self):
        out = []
        for array, struct in zip(self.generate_array_initializers(), self.generate_table_initializers()):
            out.append(f'{self.table_name}.insert({array}, {struct});')
        return out

    def generate_array_initializers(self) -> list[str]:
        out = []
        bald_headers = [hdr for hdr in self.data if '$' not in hdr]
        for row in zip(*[self.data[hdr] for hdr in bald_headers]):
            out.append(self._struct_initializer_list(f'std::array<double, {len(bald_headers)}>', [str(x) for x in row]))
        return out

    def generate_table_initializers(self) -> list[str]:
        out = []
        bald_headers = [hdr for hdr in self.data if '$' not in hdr]
        for data_row, uncert_row, citation in zip(zip(*[self.data[hdr] for hdr in bald_headers]), zip(*[self.data[hdr+'$uncertainty'] for hdr in bald_headers]), self.data['$citation']):
            data_initializer = self._struct_initializer_list('Data', [str(x) for x in data_row])
            uncert_initializer = self._struct_initializer_list('Data', [str(x) for x in uncert_row])
            citation = str(self.__class__.citations.index(citation))
            out.append(self._struct_initializer_list('TableEntry', [data_initializer, uncert_initializer, citation]))
        return out

    @staticmethod
    def _struct_initializer_list(name: str, items: list[str]):
        return f'{name}{{{", ".join(items)}}}'

    @staticmethod
    def convert_to_dataset(raw_dataset: Dict[str, List[Any]]) -> List[Tuple[Tuple[List[float], List[float]], str]]:
        headers = []
        values = []
        for header, column in raw_dataset.items():
            if '$' in header: continue
            headers.append(header)
            values.append(column)

        dataset = []
        for i, row in enumerate(zip(*values)):
            point = list(row)
            dataset.append(((point, point), str(i)))
        return dataset

    @staticmethod
    def mbr_area(bbox: List[float]) -> float:
        d = len(bbox) // 2
        return np.prod([bbox[d + i] - bbox[i] for i in range(d)])

    @staticmethod
    def compute_total_overlap(idx: index.Index) -> float:
        overlaps = 0.0
        for i in idx.intersection(idx.bounds, objects=True):
            for j in idx.intersection(i.bbox, objects=True):
                if i.id >= j.id:
                    continue
                dims = len(i.bbox) // 2
                intersection = [max(i.bbox[k], j.bbox[k]) for k in range(dims)] + \
                               [min(i.bbox[k + dims], j.bbox[k + dims]) for k in range(dims)]
                if all(intersection[k] < intersection[k + dims] for k in range(dims)):
                    overlaps += SourceBaker.mbr_area(intersection)
        return overlaps

    @staticmethod
    def evaluate_tree(entries: List[Tuple[Tuple[List[float], List[float]], str]]) -> Tuple[float, float]:
        p = index.Property()
        p.dimension = len(entries[0][0][0])
        idx = index.Index(properties=p)

        for i, (bbox, _) in enumerate(entries):
            min_corner, max_corner = bbox
            flat_bbox = tuple(min_corner + max_corner)
            assert len(flat_bbox) == 2 * p.dimension, "Bounding box dimension mismatch."
            idx.insert(i, flat_bbox)

        total_area = sum(SourceBaker.mbr_area(obj.bbox) for obj in idx.intersection(idx.bounds, objects=True))
        total_overlap = SourceBaker.compute_total_overlap(idx)

        return total_area, total_overlap

    @staticmethod
    def find_best_order(entries: List[Tuple[Tuple[List[float], List[float]], str]],
                        trials: int = 10000) -> Tuple[List[Tuple[Tuple[List[float], List[float]], str]], List[Tuple[float, List]]]:
        best_score = float('inf')
        best_order = []
        results = []

        for _ in tqdm(range(trials), desc="Testing insertion orders"):
            random.shuffle(entries)
            area, overlap = SourceBaker.evaluate_tree(entries)
            score = area + overlap
            results.append((score, list(entries)))
            if score < best_score:
                best_score = score
                best_order = list(entries)

        return best_order, results