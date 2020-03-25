python -m ingest.train_postprocess \
    --logdir /data/logs/ --modelcfg /ingestion/ingest/process/detection/src/model_config.yaml \
    --weights /data/weights/weights.pth \
    --device cuda  \
    --train_imgdir       /data/train/images \
    --train_proposalsdir /data/train/proposals \
    --train_xmldir       /data/train/annotations \
    --val_imgdir       /data/val/images \
    --val_proposalsdir /data/val/proposals \
    --val_xmldir       /data/val/annotations \
    --num_processes 120 --classcfg /ingestion/ingest/process/detection/src/classes.yaml
