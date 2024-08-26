/** @odoo-module **/

import { Component,  onMounted,  onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ProductPDFPreview extends Component {
  static template = "qxm_product_pdf_annotation_tool.ProductPDFPreview";

  setup() {
      this.rpc = useService("rpc");
      this.orm = useService("orm");
      this.active_id = this.props.id;

      onWillStart(this.fetchDocumentData.bind(this));
      onMounted(this.initializePDF.bind(this));
  }

  async fetchDocumentData() {
            this.data = await this.rpc("/web/dataset/call_kw/product.document/get_document_data", {
            model: 'product.document',
            method: 'get_document_data',
            args: [this.active_id],
            kwargs: {},
        });
        console.log(this.data);
    }
//  async fetchDocumentData() {
//        this.data = await this.rpc("/shop/product/document", {'document_id':this.active_id});
//      }

  async initializePDF() {
      try {
          const pdfContainer = document.getElementById(`pdf-container-${this.active_id}`);
          pdfContainer.addEventListener('scroll', this.onScrollPage.bind(this));
          const typedarray = this.base64ToUint8Array(this.data.pdf.datas);

          const pdf = await pdfjsLib.getDocument({ data: typedarray }).promise;
          console.log('PDF loaded');

          const pageList = document.getElementById(`page-list-${this.active_id}`);

          for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
              await this.renderPDFPage(pdf, pageNum, pdfContainer, pageList);
          }
          this.onScrollPage();
      } catch (reason) {
          console.error(reason);
      }
  }

  base64ToUint8Array(base64) {
      const binaryString = atob(base64);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
      }
      return bytes;
  }

  async renderPDFPage(pdf, pageNum, pdfContainer, pageList) {
      const page = await pdf.getPage(pageNum);
      console.log('Page loaded');

      const scale = 1.3;
      const viewport = page.getViewport({ scale });
      const pageDiv = this.createPageDiv(pageNum);
      const canvasWrapper = this.createCanvasWrapper();
      const canvas = this.createCanvas(viewport);

      canvasWrapper.appendChild(canvas);
      pageDiv.appendChild(canvasWrapper);
      pdfContainer.appendChild(pageDiv);

      const pagerCanvasWrapper = await this.createPagerCanvasWrapper(page, pageNum, pageDiv, pdfContainer);
      pageList.appendChild(pagerCanvasWrapper);

      const context = canvas.getContext('2d');
      const renderContext = { canvasContext: context, viewport };
      await page.render(renderContext).promise;
      console.log('Page rendered');

      this.initializeMarkers(pageNum, canvasWrapper, canvas);
  }

  createPageDiv(pageNum) {
      const pageDiv = document.createElement('div');
      pageDiv.id = `page-${pageNum}`;
      pageDiv.classList.add('page-div');
      return pageDiv;
  }

  createCanvasWrapper() {
      const canvasWrapper = document.createElement('div');
      canvasWrapper.classList.add('canvas-wrapper');
      return canvasWrapper;
  }

  createCanvas(viewport) {
      const canvas = document.createElement('canvas');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      return canvas;
  }

  async createPagerCanvasWrapper(page, pageNum, pageDiv, pdfContainer) {
      const pagerCanvasWrapper = document.createElement('div');
      pagerCanvasWrapper.id = `sidepage-${pageNum}`;
      pagerCanvasWrapper.classList.add('pager-canvas-wrapper');
      pagerCanvasWrapper.dataset.pageNumber = pageNum;

      const pagerViewport = page.getViewport({ scale: 0.2 });
      const pagerCanvas = this.createCanvas(pagerViewport);
      const pagerContext = pagerCanvas.getContext('2d');
      const renderPager = { canvasContext: pagerContext, viewport: pagerViewport };

      await page.render(renderPager).promise;

      const pageLink = document.createElement('div');
      pageLink.textContent = `${pageNum}`;

      pagerCanvasWrapper.appendChild(pagerCanvas);
      pagerCanvasWrapper.appendChild(pageLink);

      pagerCanvasWrapper.addEventListener('click', () => {
          this.scrollToPage(pageDiv, pdfContainer);
      });

      return pagerCanvasWrapper;
  }

  initializeMarkers(pageNum, canvasWrapper, canvas) {
      let line_count = 0;

    //   canvas.addEventListener('click', async event => {
    //       line_count += 1;
    //       const { x, y } = this.getCanvasClickPosition(event, canvas);
    //       const line_id = await this.createLine(x, y, pageNum);
    //       this.createMarkerDOM(x, y, "", line_id, canvasWrapper, pageNum, line_count);
    //   });

      const lines = this.data.lines[pageNum] || [];
      for (const line of lines) {
          line_count += 1;
          this.createMarkerDOM(line.layerx, line.layery, line.description || "", line.id, canvasWrapper, pageNum, line_count);
      }
  }

//   getCanvasClickPosition(event, canvas) {
//       const rect = canvas.getBoundingClientRect();
//       const x = event.clientX - rect.left;
//       const y = event.clientY - rect.top;
//       return { x, y };
//   }

  createMarkerDOM(x, y, description, line_id, canvasWrapper, pageNum, line_count) {
      const markerDiv = this.createMarkerDiv(x, y, line_id);
      canvasWrapper.appendChild(markerDiv);

      const newTableRow = this.createTableRow(line_id, description, pageNum, line_count, markerDiv);
      var table_tbody = document.getElementById(`table_tbody_${this.active_id}`)
      table_tbody.appendChild(newTableRow);  
  }

  createMarkerDiv(x, y, line_id) {
      const markerDiv = document.createElement('div');
      markerDiv.style.left = `${x}px`;
      markerDiv.style.top = `${y}px`;
      markerDiv.id = `marker_${line_id}`;
      markerDiv.classList.add('img_marker');
      return markerDiv;
  }

  async createLine(x, y, page_no) {
      const [line_id] = await this.orm.create("product.pdf.annotation.line", [{
          page_no,
          layerx: x,
          layery: y,
          document_id: this.active_id
      }]);
      return line_id;
  }

  async updateLine(resId, data) {
      await this.orm.write("product.pdf.annotation.line", [resId], data);
  }

  createTableRow(rowId, description, pageNumber, lineNumber, markerDiv) {
      const tr = document.createElement('tr');
      tr.id = `table_line_${rowId}`;
      tr.className = 'table_tr_line';

      tr.innerHTML = `
          <th scope="row"><span>${pageNumber}</span></th>
          <td><span>${description}</span></td>
      `;

      tr.onmouseover = () => this.addHoverEffect(markerDiv, tr);
      tr.onmouseout = () => this.removeHoverEffect();
      tr.onclick = () => this.scrollToElement(markerDiv);

      markerDiv.onmouseover = () => this.addHoverEffect(markerDiv, tr);
      markerDiv.onmouseout = () => this.removeHoverEffect();
      markerDiv.onclick = () => this.scrollToElement(tr);

      //this.initializeDeleteMarker(tr, markerDiv, rowId);
      //this.initializeSaveMarker(tr, rowId);

      return tr;
  }

  addHoverEffect(markerDiv, tr) {
      document.querySelectorAll('.marker_hover').forEach(el => el.classList.remove('marker_hover'));
      markerDiv.classList.add('marker_hover');
      tr.classList.add('marker_hover');
  }

  removeHoverEffect() {
      document.querySelectorAll('.marker_hover').forEach(el => el.classList.remove('marker_hover'));
  }

  scrollToElement(element) {
      const container = document.getElementById(element.classList.contains('img_marker') ? `pdf-container-${this.active_id}` : `description_container_${this.active_id}`);
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();

      const scrollTop = (elementRect.top - 200) - containerRect.top + container.scrollTop;

      container.scrollTo({ top: scrollTop, behavior: 'smooth' });
  }

//   initializeDeleteMarker(tr, markerDiv, rowId) {
//       const deleteIcon = tr.querySelector('.delete_marker');
//       deleteIcon.onclick = () => {
//           tr.remove();
//           markerDiv.remove();
//           this.orm.unlink("product.pdf.annotation.line", [rowId]);
//       };
//   }

//   initializeSaveMarker(tr, rowId) {
//       const inputField = tr.querySelector('.table_tbody_input');
//       inputField.onchange = () => {
//           this.updateLine(rowId, { description: inputField.value });
//       };
//   }

  onScrollPage() {
      const pages = document.getElementById(`pdf-container-${this.active_id}`).querySelectorAll('[id^="page-"]');
      const pagerItems = document.getElementById(`page-list-${this.active_id}`).querySelectorAll('[id^="sidepage-"]');
      const scrollTop = document.getElementById(`pdf-container-${this.active_id}`).scrollTop;
      const containerHeight = document.getElementById(`pdf-container-${this.active_id}`).clientHeight;

      let currentPage = 0;
      pages.forEach((page, index) => {
          if (scrollTop >= page.offsetTop - containerHeight / 2) {
              currentPage = index;
          }
      });

      pagerItems.forEach((item, index) => {
          if (index === currentPage) {
              item.firstChild.classList.add('active');
              document.getElementById(`page-list-${this.active_id}`).scrollTop = item.offsetTop - document.getElementById(`page-list-${this.active_id}`).clientHeight / 2;
          } else {
              item.firstChild.classList.remove('active');
          }
      });
  }

  scrollToPage(pageDiv, pdfContainer) {
      const containerRect = pdfContainer.getBoundingClientRect();
      const pageRect = pageDiv.getBoundingClientRect();
      const scrollTop = pageRect.top - containerRect.top + pdfContainer.scrollTop;

      pdfContainer.scrollTop = scrollTop;
  }
}

registry.category("actions").add("qxm_product_pdf_annotation_tool.product_pdf_preview", ProductPDFPreview);
