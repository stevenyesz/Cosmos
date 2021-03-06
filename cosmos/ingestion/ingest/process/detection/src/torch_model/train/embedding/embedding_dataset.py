"""
Dataset class for training an
Image embedding
"""
import torch
from ingest.process.detection.src.torch_model.train.data_layer.xml_loader import XMLLoader, Example, get_radii, get_angles, get_colorfulness
from ingest.process.detection.src.utils.ingest_images import get_example_for_uuid, ImageDB
import random


class ImageEmbeddingDataset(XMLLoader):
    def __init__(self, ingest_objs, classes, session):
        """
        Create an image embedding db
        :param db: a sqlalchemy session to query for images
        """
        super(ImageEmbeddingDataset, self).__init__(ingest_objs, classes, session)


    @staticmethod
    def collate(batch):
        return XMLLoader.collate(batch)

    def __getitem__(self, item):
        if item < len(self.uuids):
            item =  XMLLoader.__getitem__(self, item)
            item.label = torch.ones(1)
        # If item is out of index, grab a random obj and generate a negative sample
        uuid = random.choice(self.uuids)
        session = ImageDB.build()
        ex = get_example_for_uuid(uuid, session)
        label = torch.zeros(1)
        # We pass False here, which generates negative neighbors
        neighbors = ex.neighbors(False, self.uuids, session)
        neighbor_boxes = [n.bbox for n in neighbors]
        neighbor_windows = [n.window for n in neighbors]
        radii = get_radii(ex.bbox, torch.stack(neighbor_boxes))
        angles = get_angles(ex.bbox, torch.stack(neighbor_boxes))
        colorfulness = get_colorfulness(ex.window)
        return Example(ex.bbox, label, ex.window, neighbor_boxes, neighbor_windows, radii, angles,colorfulness)

    def __len__(self):
        return 2 * len(self.uuids)
