"""
Train entry point
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import torch
from hyperyaml.hyperyaml import HyperYaml
from ingest.process.detection.src.torch_model.model.model import MMFasterRCNN
from ingest.process.detection.src.torch_model.train.train import TrainerHelper
from ingest.process.detection.src.torch_model.model.utils.config_manager import ConfigManager
from ingest.process.detection.src.torch_model.train.data_layer.xml_loader import XMLLoader
from ingest.process.detection.src.torch_model.train.data_layer.sql_types import Base
from ingest.process.detection.src.torch_model.train.embedding.embedding_dataset import ImageEmbeddingDataset
from ingest.process.detection.src.utils.ingest_images import ImageDB
import yaml
from os.path import join
import click

def get_img_dir(root):
    return join(root,"images")

def get_anno_dir(root):
    return join(root, "annotations")

def get_proposal_dir(root):
    return join(root, "proposals")

def get_dataset(dir, warped_size, expansion_delta, img_type, partition, cfg):
    engine = create_engine('sqlite:///:memory:')  
    Base.metadata.create_all(engine)
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session() 
    ingest_objs = ImageDB.initialize_and_ingest((get_img_dir(dir),
                                                         get_proposal_dir(dir),
                                                         get_anno_dir(dir)),
                                                         warped_size,
                                                         partition,
                                                         expansion_delta, session)
    dataset = XMLLoader(ingest_objs, cfg.CLASSES, session)
    embedding_dataset = ImageEmbeddingDataset(ingest_objs, cfg.CLASSES, session)
    session.close()
    return dataset

class ModelBuilder:
    def __init__(self,val_dir, train_dir, start_config="model_config.yaml", device=torch.device("cuda"), start_train="train_config.yaml", pretrain_weights=None):
        self.config = ConfigManager(start_config)
        warped_size = self.config.WARPED_SIZE
        expansion_delta = self.config.EXPANSION_DELTA
        self.pretrain_weights = pretrain_weights
        self.device = device
        with open(start_train) as stream:
            self.train_config = yaml.load(stream)
        self.train_set = get_dataset(train_dir, warped_size, expansion_delta, "png", 'train', self.config)
        self.val_set = get_dataset(val_dir, warped_size, expansion_delta, "png", 'val', self.config)

    def build(self, params):
        self.build_cfg(params)
        self.build_train_cfg(params)
        model = MMFasterRCNN(self.config)
        if self.pretrain_weights is not None:
            model_dict = model.state_dict()
            pretrained_dict = torch.load(self.pretrain_weights, map_location=self.device)
            filter = ['head.cls_branch.weight', 'head.cls_branch.bias']
            pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict and k not in filter}
            model_dict.update(pretrained_dict)
            model.load_state_dict(model_dict)
        # TODO the params object shouldn't have any reason to leak into
        trainer = TrainerHelper(model, self.train_set, self.val_set,self.train_config, self.device)
        trainer.train()
        loss = trainer.validate()
        return loss

    def build_train_cfg(self, params):
        for key in self.train_config.keys():
            if key in params:
                self.train_config[key] = params[key]

    def build_cfg(self, params):
        print(params)
        for key in params.keys():
            if hasattr(self.config, key):
                setattr(self.config, key, params[key])

def build_model(hyperopt_config, max_evals, val_dir, train_dir, weights_dir, train_config, model_config, pretrain_weights):
    builder = ModelBuilder(val_dir, train_dir, start_train=train_config, start_config=model_config, pretrain_weights=pretrain_weights)
    hyp = HyperYaml(hyperopt_config,builder, max_evals)
    hyp.run()
    hyp.write(join(weights_dir, "best.yaml"))

@click.command()
@click.option('--hyperopt-config', type=str, help='Path to hyperopt config')
@click.option('--max-evals', type=int, help='Number of hyperopt evals')
@click.option('--train-dir', type=str, help='Path to train directory')
@click.option('--val-dir', type=str, help='Path to validation directory')
@click.option('--weights-dir', type=str, help='Path to write weights directory')
@click.option('--train-config', type=str, help='Train config file path')
@click.option('--model-config', type=str, help='Model config file path')
@click.option('--pretrain-weights', type=str, help='Path to pretrained weights')
def run(hyperopt_config, max_evals, train_dir, val_dir, weights_dir, train_config, model_config, pretrain_weights):
    build_model(hyperopt_config, max_evals, val_dir, train_dir, weights_dir, train_config, model_config, pretrain_weights)

if __name__ == "__main__":
    run()

