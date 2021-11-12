# -*- coding: utf-8 -*-
# Copyright 2021 PT. Simetri Sinergi Indonesia
# Copyright 2021 OpenSynergy Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

import pytz
from openerp import api, fields, models
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class CreateDJBCFullfilmentInvoice(models.TransientModel):
    _name = "l10n_id.create_djbc_fullfilment_invoice"
    _description = "Create DJBC Fullfilment Invoice"

    @api.model
    def _default_document_id(self):
        return self.env.context.get("active_id", False)

    document_id = fields.Many2one(
        string="# Document",
        comodel_name="l10n_id.djbc_custom_document",
        required=True,
        default=lambda self: self._default_document_id(),
    )

    date_start = fields.Date(
        string="Date Start",
    )
    date_end = fields.Date(
        string="Date End",
    )
    date_invoice = fields.Date(
        string="Date Invoice",
    )
    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        required=True,
    )

    @api.multi
    @api.depends(
        "currency_id",
    )
    def _compute_allowed_journal_ids(self):
        obj_journal = self.env["account.journal"]
        for wizard in self:
            if wizard.currency_id:
                if wizard.currency_id == self.env.user.company_id.currency_id:
                    currency_id = False
                else:
                    currency_id = wizard.currency_id.id

                criteria = [
                    ("currency", "=", currency_id),
                    ("type", "=", "sale"),
                ]
                wizard.allowed_journal_ids = obj_journal.search(criteria).ids
            else:
                wizard.allowed_journal_ids = []

    allowed_journal_ids = fields.Many2many(
        string="Allowed Journals",
        comodel_name="account.journal",
        compute="_compute_allowed_journal_ids",
        store=False,
    )
    journal_id = fields.Many2one(
        string="Journal",
        comodel_name="account.journal",
        domain=[
            ("type", "=", "sale"),
        ],
    )

    @api.multi
    def _prepare_domain_fullfilment_service(self):
        self.ensure_one()
        domain = [("id", "=", 0)]
        domain = [
            ("currency_id", "=", self.currency_id.id),
            ("item_id.applicable_on", "=", "move"),
            ("invoice_id", "=", False),
            ("move_id", "!=", False),
            ("move_id.djbc_custom_document_id", "=", self.document_id.id),
            ("move_id.djbc_custom", "=", True),
        ]
        if self.date_start:
            date_start = self._convert_datetime_utc(self.date_start + " 00:00:00")
            domain += [("move_id.date", ">=", date_start)]
        if self.date_end:
            date_end = self._convert_datetime_utc(self.date_end + " 23:59:59")
            domain += [("move_id.date", "<=", date_end)]
        return domain

    @api.depends(
        "date_start",
        "date_end",
    )
    @api.multi
    def _compute_allowed_fullfilment_service_ids(self):
        self.ensure_one()
        obj_stock_fulfillment_service = self.env["stock.fulfillment_service"]
        fulfillment_service_ids = obj_stock_fulfillment_service.search(
            self._prepare_domain_fullfilment_service()
        )
        self.allowed_fulfillment_service_ids = fulfillment_service_ids.ids

    allowed_fulfillment_service_ids = fields.Many2many(
        string="Allowed Services",
        comodel_name="stock.fulfillment_service",
        compute="_compute_allowed_fullfilment_service_ids",
        store=False,
    )

    fulfillment_service_ids = fields.Many2many(
        string="Fullfilment Services",
        comodel_name="stock.fulfillment_service",
        relation="rel_djbc_custom_document_2_fullfilment_service",
        column1="document_id",
        column2="fulfillment_service_id",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("populate", "Populate"),
        ],
        string="State",
        default="draft",
        readonly=True,
    )

    @api.multi
    def _convert_datetime_utc(self, dt):
        user = self.env.user
        if user.tz:
            local = pytz.timezone(user.tz)
        else:
            local = pytz.utc
        naive = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        local_dt = local.localize(naive, is_dst=None)
        convert_utc = local_dt.astimezone(pytz.utc)
        format_utc = datetime.strftime(convert_utc, DEFAULT_SERVER_DATETIME_FORMAT)
        return format_utc

    @api.multi
    def action_create_fullfilment_invoice(self):
        self.ensure_one()
        obj_invoice = self.env["account.invoice"]
        obj_invoice_line = self.env["account.invoice.line"]
        invoices = {}
        invoice_ids = []
        for line in self.fulfillment_service_ids.filtered(
            lambda r: r.currency_id.id == self.currency_id.id
        ):
            invoice_id = invoices.get(line.partner_id.id, False)
            if not invoice_id:
                invoice = obj_invoice.create(self._prepare_invoice(line.partner_id))
                invoices[line.partner_id.id] = invoice.id
                invoice_ids.append(invoice.id)
            inv_line = obj_invoice_line.create(
                self._prepare_invoice_line(invoice, line)
            )
            line.write({"invoice_line_id": inv_line.id})
        self.document_id.fullfilment_invoice_ids = [
            (4, invoice_id) for invoice_id in invoice_ids
        ]

    @api.multi
    def _prepare_invoice(self, partner):
        self.ensure_one()
        return {
            "partner_id": partner.id,
            "date_invoice": self.date_invoice,
            "journal_id": self.journal_id.id,
            "account_id": partner.property_account_receivable.id,
        }

    @api.multi
    def _prepare_invoice_line(self, invoice, fulfillment_service):
        self.ensure_one()
        account_id = fulfillment_service.item_id.product_id._get_processing_account_id()
        return {
            "invoice_id": invoice.id,
            "name": fulfillment_service.name,
            "product_id": fulfillment_service.item_id.product_id.id,
            "account_id": account_id,
            "quantity": fulfillment_service.quantity,
            "uos_id": fulfillment_service.uom_id.id,
            "price_unit": fulfillment_service.price_unit,
            "invoice_line_tax_id": fulfillment_service.tax_ids.ids,
        }

    @api.multi
    def action_populate_fullfilment_service(self):
        self.ensure_one()
        self.state = "populate"
        self.fulfillment_service_ids = self.allowed_fulfillment_service_ids.ids
        return {
            "context": self.env.context,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "l10n_id.create_djbc_fullfilment_invoice",
            "res_id": self.id,
            "view_id": False,
            "type": "ir.actions.act_window",
            "target": "new",
        }

    @api.multi
    def action_previous(self):
        self.ensure_one()
        self.state = "draft"
        self.fulfillment_service_ids = False
        return {
            "context": self.env.context,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "l10n_id.create_djbc_fullfilment_invoice",
            "res_id": self.id,
            "view_id": False,
            "type": "ir.actions.act_window",
            "target": "new",
        }
