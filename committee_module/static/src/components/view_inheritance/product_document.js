/** @odoo-module **/

import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { ProductDocumentKanbanController } from "@product/js/product_document_kanban/product_document_kanban_controller";
import { ProductDocumentKanbanRenderer } from "@product/js/product_document_kanban/product_document_kanban_renderer";
import {ProductDocumentKanbanControllerInherits} from "./kanbancontroller";

export const productDocumentKanbanViewInherit = {
    ...kanbanView,
    Controller: ProductDocumentKanbanControllerInherits,
    Renderer: ProductDocumentKanbanRenderer,
    buttonTemplate: "product.ProductDocumentKanbanView.Buttons.inherit",
};

registry.category("views").add("product_documents_kanban_inherit", productDocumentKanbanViewInherit);
