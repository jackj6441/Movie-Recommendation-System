import argparse
import os

import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint

from config import DataConfig
from data import MovieLensDataModule
from lightning_ncf import LightningNCF


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NCF training entrypoint")
    parser.add_argument("--dry_run", action="store_true", help="only run data sanity check")
    parser.add_argument("--data_path", type=str, default=None, help="path to ratings.csv")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--num_neg", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument(
        "--amp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="enable mixed precision when supported",
    )
    parser.add_argument("--grad_accum", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = DataConfig(
        batch_size=args.batch_size,
        num_neg=args.num_neg,
        seed=args.seed,
        ratings_csv_path=args.data_path,
    )

    data_module = MovieLensDataModule(
        batch_size=config.batch_size,
        num_neg=config.num_neg,
        seed=config.seed,
        ratings_csv_path=config.ratings_csv_path,
    )
    data_module.prepare_data()

    if args.num_neg > 0:
        print("Note: num_neg is ignored in explicit rating mode.")

    if args.dry_run:
        data_module.sanity_check()
        return

    pl.seed_everything(config.seed, workers=True)
    model = LightningNCF(
        num_users=data_module.num_users,
        num_items=data_module.num_items,
        lr=args.lr,
    )

    use_amp = args.amp and torch.cuda.is_available()
    precision = "16-mixed" if use_amp else 32
    checkpoint_dir = os.path.join("training", "checkpoints")
    checkpoint_callback = ModelCheckpoint(
        dirpath=checkpoint_dir,
        filename="ncf-{epoch:02d}-{val_rmse:.4f}",
        monitor="val_rmse",
        mode="min",
        save_top_k=1,
    )
    early_stopping = EarlyStopping(monitor="val_rmse", mode="min", patience=2)

    trainer = pl.Trainer(
        max_epochs=args.epochs,
        precision=precision,
        accumulate_grad_batches=args.grad_accum,
        callbacks=[checkpoint_callback, early_stopping],
        log_every_n_steps=50,
        accelerator="auto",
        devices="auto",
    )

    trainer.fit(
        model,
        train_dataloaders=data_module.train_dataloader(),
        val_dataloaders=data_module.val_dataloader(),
    )
    trainer.test(model, dataloaders=data_module.test_dataloader(), ckpt_path="best")


if __name__ == "__main__":
    main()
