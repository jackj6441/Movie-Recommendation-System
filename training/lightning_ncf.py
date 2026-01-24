import torch
import pytorch_lightning as pl
from torch import nn

from model_ncf import NCF


class LightningNCF(pl.LightningModule):
    def __init__(
        self,
        num_users: int,
        num_items: int,
        lr: float = 1e-3,
        embedding_dim: int = 64,
        mlp_layers: tuple[int, ...] = (128, 64, 32),
    ) -> None:
        super().__init__()
        self.save_hyperparameters()
        self.model = NCF(
            num_users=num_users,
            num_items=num_items,
            embedding_dim=embedding_dim,
            mlp_layers=mlp_layers,
        )
        self.loss_fn = nn.MSELoss()

    def forward(self, user_idx: torch.Tensor, item_idx: torch.Tensor) -> torch.Tensor:
        return self.model(user_idx, item_idx)

    def training_step(self, batch: tuple[torch.Tensor, ...], batch_idx: int) -> torch.Tensor:
        user_idx, item_idx, label = batch
        preds = self(user_idx, item_idx)
        loss = self.loss_fn(preds, label)
        self.log("train_loss", loss, on_step=False, on_epoch=True, prog_bar=True)
        return loss

    def validation_step(self, batch: tuple[torch.Tensor, ...], batch_idx: int) -> None:
        user_idx, item_idx, label = batch
        preds = self(user_idx, item_idx)
        preds = torch.clamp(preds, 0.5, 5.0)
        rmse = torch.sqrt(torch.mean((preds - label) ** 2))
        self.log("val_rmse", rmse, on_step=False, on_epoch=True, prog_bar=True)

    def test_step(self, batch: tuple[torch.Tensor, ...], batch_idx: int) -> None:
        user_idx, item_idx, label = batch
        preds = self(user_idx, item_idx)
        preds = torch.clamp(preds, 0.5, 5.0)
        rmse = torch.sqrt(torch.mean((preds - label) ** 2))
        self.log("test_rmse", rmse, on_step=False, on_epoch=True, prog_bar=True)

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.hparams.lr, weight_decay=1e-5)
