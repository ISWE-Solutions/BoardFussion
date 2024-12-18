/** @odoo-module **/

import { Component, onMounted, onWillStart, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { pdfjsLib } from 'pdfjs-dist';

class MergePreview extends Dialog {
  static template = "odoo_calendar_inheritence.PDFCustomPreview";

  setup() {
    this.rpc = useService("rpc");
    this.orm = useService("orm");
    this.table_tbody = useRef("table_tbody");
    this.display = {
      controlPanel: {},
      searchPanel: false,
    };
    this.active_id = this.props.action.context.active_id;
    this.pdfContainer = useRef("pdf-container");
  }

  willStart() {
    return this._rpc({
      model: 'ir.attachment',
      method: 'read',
      args: [[this.props.params.attachment_id], ['datas', 'name', 'mimetype']],
    }).then(attachment => {
      this.attachment = attachment[0];
      this.renderPDF();
    });
  }

  renderPDF() {
    const pdfContainer = this.pdfContainer.el;
    pdfjsLib.GlobalWorkerOptions.workerSrc = '/web/static/lib/pdfjs-dist/build/pdf.worker.js';
    const pdfDoc = pdfjsLib.getDocument({data: atob(this.attachment.datas)});
    pdfDoc.promise.then(pdf => {
      const scale = 1.5;
      const viewport = pdf.getPage(1).getViewport({scale: scale});
      const canvas = document.createElement('canvas');
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      pdfContainer.appendChild(canvas);
      const context = canvas.getContext('2d');
      pdf.getPage(1).render({canvasContext: context, viewport: viewport});
    });
  }

  _onDownload() {
    const a = document.createElement('a');
    a.href = `data:${this.attachment.mimetype};base64,${this.attachment.datas}`;
    a.download = this.attachment.name;
    a.click();
  }

  get events() {
    return {
      'click .btn-download': '_onDownload',
    };
  }
}

registry.category("actions").add("odoo_calendar_inheritence.merge_preview", MergePreview);