#!/usr/bin/env python3
"""Private preview server for this website, with an optional in-page editor.

    python3 scripts/preview_server.py              # http://127.0.0.1:8741/
    python3 scripts/preview_server.py --port 8000

The server binds to 127.0.0.1 only, so nobody but this computer can open it.
Every response carries no-cache headers, so a plain reload always shows the
latest saved file.

Editor: open  http://127.0.0.1:8741/#edit  (Edit.command does this for you).
A small toolbar appears. Click a paragraph, heading, caption, list item or
publication entry and type; select words for Bold, Italic or Link. Enter
starts a new paragraph or entry, Backspace on an empty one removes it. Each
block has Move up/down, Duplicate and Delete. "Add..." offers page-specific
blocks: journal paper / book chapter / preprint, lab member (with photo),
research section (with its "On this page" link), a paragraph or a figure.
Click a picture to replace it (same file name), swap in another file, or set
its alt text. Save writes the change into the real HTML file in this folder;
pictures are written into images/ as soon as they are chosen. The lab name
field writes js/site-config.js. Size and Width presets on a block, Size on a
picture, and the site-wide A-/A+ text size (written to css/styles.css) pick
from the design's own scale; colours and layout are not edited here.

Before each save the previous version of the file is copied to
  macOS:  ~/Library/Application Support/Lab website preview/backups/
  other:  ~/.lab-website-preview/backups/
The editor is a local tool only; its script is injected into pages as they
are served and is never written into the files.
"""
import argparse
import datetime
import functools
import http.server
import json
import os
import posixpath
import re
import shutil
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "darwin":
    BACKUP_DIR = os.path.expanduser(
        "~/Library/Application Support/Lab website preview/backups")
else:
    BACKUP_DIR = os.path.expanduser("~/.lab-website-preview/backups")

EDITABLE_EXT = (".html",)
CONFIG_FILE = "js/site-config.js"

EDITOR_CSS = r"""
.lsed{outline:1px dashed rgba(70,95,125,.45);outline-offset:3px;cursor:text;min-height:1em;border-radius:2px}
.lsed:hover{outline-color:rgba(70,95,125,.85)}
.lsed:focus{outline:2px solid #4a76a8;outline-offset:3px;background:rgba(120,160,200,.10)}
.lsed-img{outline:1px dashed rgba(70,95,125,.45);outline-offset:3px;cursor:pointer}
.lsed-img:hover,.lsed-img.lsed-active{outline:2px solid #4a76a8}
.lsed-bar{position:fixed;right:16px;bottom:16px;z-index:2147483000;display:flex;flex-direction:column;gap:6px;
  background:#24303d;color:#fff;padding:9px 12px;border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.28);
  font:500 13px/1.3 Inter,system-ui,-apple-system,sans-serif;max-width:calc(100vw - 32px)}
.lsed-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.lsed-bar b{font-weight:600;color:#cfe0f2}
.lsed-bar button,.lsed-mini button,.lsed-menu button{font:inherit;border:0;border-radius:8px;padding:6px 10px;cursor:pointer;
  background:#3b4b5d;color:#fff;white-space:nowrap}
.lsed-bar button:hover,.lsed-mini button:hover,.lsed-menu button:hover{background:#4a5d72}
.lsed-bar button.lsed-primary{background:#6f9ac4;color:#0f1a26}
.lsed-bar button.lsed-primary:hover{background:#8ab1d6}
.lsed-bar button:disabled{opacity:.45;cursor:default}
.lsed-status{color:#b9c6d4;min-width:7em}
.lsed-mini{display:flex;gap:4px;align-items:center;flex-wrap:wrap;padding-top:6px;border-top:1px solid #3b4b5d;font-size:12px}
.lsed-mini button{padding:4px 8px}
.lsed-mini .lsed-label{color:#b9c6d4;margin-right:4px}
.lsed-bar select{font:inherit;font-size:12px;border:0;border-radius:8px;padding:4px 6px;background:#3b4b5d;color:#fff;cursor:pointer}
.lsed-scale{display:inline-flex;align-items:center;gap:2px;margin-left:4px}
.lsed-scale button{padding:4px 7px}
.lsed-scale span{min-width:3.2em;text-align:center;color:#cfe0f2;font-size:12px}
.lsed-mini .lsed-sep{width:1px;height:18px;background:#4a5d72;margin:0 2px}
.lsed-mini button.lsed-danger{background:#7a3b3b}
.lsed-mini button.lsed-danger:hover{background:#934848}
.lsed-mini button.lsed-fmt{font-weight:700;min-width:28px;text-align:center}
.lsed-menu{position:fixed;right:16px;bottom:66px;z-index:2147483001;display:flex;flex-direction:column;gap:4px;
  background:#24303d;padding:8px;border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.28);
  font:500 13px/1.3 Inter,system-ui,-apple-system,sans-serif}
.lsed-menu button{text-align:left}
.lsed-menu .lsed-menu-title{color:#b9c6d4;font-size:12px;padding:2px 4px 4px}
.lsed-hidden{display:none !important}
"""

EDITOR_JS = r"""
(function () {
  'use strict';
  var script = document.currentScript;
  var PATH = script && script.getAttribute('data-path');
  var KEY = 'labsite.editmode';
  if (location.hash === '#edit') {
    try { localStorage.setItem(KEY, '1'); } catch (e) {}
    history.replaceState(null, '', location.pathname + location.search);
  }
  var on = false;
  try { on = localStorage.getItem(KEY) === '1'; } catch (e) {}
  if (!on || !PATH) { return; }

  var main = document.querySelector('main');
  if (!main) { return; }

  var PREFIX = PATH.indexOf('/') !== -1 ? '../' : '';
  var PAGE = PATH === 'index.html' ? 'home' : PATH.split('/')[0];
  var SEL = 'h1,h2,h3,h4,p,li,dt,dd,figcaption,summary';
  var IMG_EXT = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'];
  var dirty = false;
  var current = null;      // focused editable text element
  var currentImg = null;   // selected image

  // ---------- small helpers ----------
  function all(root, sel) { return Array.prototype.slice.call(root.querySelectorAll(sel)); }
  function candidates(root) {
    return all(root, SEL).filter(function (el) {
      return !el.querySelector(SEL) && !el.closest('[data-config]');
    });
  }
  function makeEditable(el) {
    el.setAttribute('contenteditable', 'true');
    el.setAttribute('spellcheck', 'true');
    el.classList.add('lsed');
  }
  function prepImages(root) {
    all(root, 'img').forEach(function (img) { img.classList.add('lsed-img'); });
  }
  function blockOf(el) {
    return el.closest('li') || el.closest('dl > div') || el;
  }
  function moveTargetOf(el) {
    var li = el.closest('li') || el.closest('dl > div');
    if (li) { return li; }
    if (el.tagName === 'H2' && el.closest('section[id]')) { return el.closest('section[id]'); }
    return el;
  }
  function blockLabel(el) {
    var b = blockOf(el);
    if (b.classList && b.classList.contains('member')) { return 'person'; }
    if (b.classList && b.classList.contains('citation')) { return 'publication'; }
    return b === el ? 'block' : 'entry';
  }
  function placeCaret(el, atEnd) {
    var range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(!atEnd);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    el.focus();
  }
  function caretAtStart(el) {
    var sel = window.getSelection();
    if (!sel.rangeCount || !sel.isCollapsed) { return false; }
    var r = sel.getRangeAt(0).cloneRange();
    r.selectNodeContents(el);
    r.setEnd(sel.anchorNode, sel.anchorOffset);
    return r.toString().length === 0;
  }
  function indentBefore(node) {
    var prev = node.previousSibling;
    if (prev && prev.nodeType === 3) {
      var m = /\n([ \t]*)$/.exec(prev.nodeValue);
      if (m) { return '\n' + m[1]; }
    }
    return '\n';
  }
  function insertAfterBlock(block, node) {
    block.after(document.createTextNode(indentBefore(block)), node);
  }
  function insertFirstChild(parent, node) {
    var firstEl = parent.firstElementChild;
    if (firstEl) { firstEl.before(node, document.createTextNode(indentBefore(firstEl))); return; }
    appendChildBlock(parent, node);
  }
  function wsChild(parent) {
    // Whitespace to put before a new last child of `parent`.
    var lastEl = parent.lastElementChild;
    return lastEl ? indentBefore(lastEl) : indentBefore(parent) + '  ';
  }
  function appendChildBlock(parent, node) {
    var lastEl = parent.lastElementChild;
    if (lastEl) { lastEl.after(document.createTextNode(indentBefore(lastEl)), node); return; }
    var base = indentBefore(parent);
    if (parent.textContent.trim() === '') { while (parent.firstChild) { parent.removeChild(parent.firstChild); } }
    parent.appendChild(document.createTextNode(base + '  '));
    parent.appendChild(node);
    parent.appendChild(document.createTextNode(base));
  }
  function removeBlock(block) {
    var prev = block.previousSibling;
    if (prev && prev.nodeType === 3 && !prev.nodeValue.trim()) { prev.remove(); }
    block.remove();
  }
  function moveBlock(b, dir) {
    var sib = dir < 0 ? b.previousElementSibling : b.nextElementSibling;
    if (!sib) { return false; }
    var ws = indentBefore(b);
    var prev = b.previousSibling;
    if (prev && prev.nodeType === 3 && !prev.nodeValue.trim()) { prev.remove(); }
    if (dir < 0) {
      // Go in front of the sibling *and* the whitespace that precedes it, so the sibling keeps its own line.
      var anchor = (sib.previousSibling && sib.previousSibling.nodeType === 3 && !sib.previousSibling.nodeValue.trim()) ? sib.previousSibling : sib;
      anchor.before(document.createTextNode(ws), b);
    } else {
      sib.after(document.createTextNode(ws), b);
    }
    return true;
  }
  function html(str, ws) {
    // Build an element from a zero-indented template, re-indented to sit after whitespace `ws`.
    var ind = (ws || '\n').slice(1);
    var t = document.createElement('template');
    t.innerHTML = str.trim().replace(/\n/g, '\n' + ind);
    return t.content.firstElementChild;
  }
  function slugify(s) {
    return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'section';
  }
  function uniqueId(base) {
    var id = base, n = 2;
    while (document.getElementById(id)) { id = base + '-' + n; n += 1; }
    return id;
  }
  function extOf(name) { var m = /\.([A-Za-z0-9]+)$/.exec(name || ''); return m ? m[1].toLowerCase() : ''; }
  function sameExt(a, b) { a = a === 'jpeg' ? 'jpg' : a; b = b === 'jpeg' ? 'jpg' : b; return a === b; }
  function safeFileName(name) {
    var ext = extOf(name);
    var base = name.replace(/\.[A-Za-z0-9]+$/, '').normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'image';
    return base + (ext ? '.' + ext : '');
  }
  function siteRel(src) {
    // "../images/x.png" or "images/x.png" -> "images/x.png"
    var u = (src || '').split('?')[0].split('#')[0];
    if (/^[a-z]+:/i.test(u) || u.charAt(0) === '/') { return null; }
    return u.replace(/^(\.\.\/)+/, '').replace(/^\.\//, '');
  }
  function markDirty(msg) {
    dirty = true;
    saveBtn.disabled = false;
    status.textContent = msg || 'Unsaved changes';
  }
  function imageSize(file) {
    return new Promise(function (resolve) {
      if (extOf(file.name) === 'svg') { resolve(null); return; }
      var url = URL.createObjectURL(file);
      var im = new Image();
      im.onload = function () { resolve({ w: im.naturalWidth, h: im.naturalHeight }); URL.revokeObjectURL(url); };
      im.onerror = function () { resolve(null); URL.revokeObjectURL(url); };
      im.src = url;
    });
  }
  function pickFile(accept) {
    return new Promise(function (resolve) {
      var input = document.createElement('input');
      input.type = 'file';
      if (accept) { input.accept = accept; }
      input.className = 'lsed-hidden';
      document.body.appendChild(input);
      input.addEventListener('change', function () { resolve(input.files[0] || null); input.remove(); });
      window.addEventListener('focus', function onFocus() {
        window.removeEventListener('focus', onFocus);
        setTimeout(function () { if (document.body.contains(input)) { resolve(null); input.remove(); } }, 800);
      });
      input.click();
    });
  }
  function upload(rel, file, mode) {
    return fetch('/__edit/upload?path=' + encodeURIComponent(rel) + '&mode=' + mode, {
      method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file
    }).then(function (r) {
      return r.json().then(function (j) { j.status = r.status; return j; });
    });
  }
  function uploadNew(rel, file) {
    return upload(rel, file, 'new').then(function (j) {
      if (j.status === 409) {
        if (!window.confirm('A file named ' + rel + ' already exists. Replace it?')) { return null; }
        return upload(rel, file, 'replace');
      }
      return j;
    }).then(function (j) {
      if (j && j.status && j.status !== 200) { throw new Error(j.error || ('upload failed (' + j.status + ')')); }
      return j;
    });
  }

  // ---------- set up editable content ----------
  all(main, 'details').forEach(function (d) { d.setAttribute('data-lsed-open', d.open ? '1' : '0'); });
  candidates(main).forEach(makeEditable);
  prepImages(main);

  // ---------- toolbar ----------
  var bar = document.createElement('div');
  bar.className = 'lsed-bar';
  var row = document.createElement('div');
  row.className = 'lsed-row';
  row.innerHTML = '<span>Editing <b></b></span>';
  row.querySelector('b').textContent = PATH;
  bar.appendChild(row);
  var saveBtn = document.createElement('button');
  saveBtn.textContent = 'Save';
  saveBtn.className = 'lsed-primary';
  saveBtn.disabled = true;
  var addBtn = document.createElement('button');
  addBtn.textContent = 'Add…';
  var nameBtn = document.createElement('button');
  nameBtn.textContent = 'Lab name…';
  var exitBtn = document.createElement('button');
  exitBtn.textContent = 'Exit editing';
  var status = document.createElement('span');
  status.className = 'lsed-status';
  status.textContent = 'Click text or an image to edit';
  var scaleBox = document.createElement('span');
  scaleBox.className = 'lsed-scale';
  scaleBox.title = 'Site-wide text size (written to css/styles.css)';
  var scaleDown = document.createElement('button'); scaleDown.textContent = 'A\u2212';
  var scaleRead = document.createElement('span');
  var scaleUp = document.createElement('button'); scaleUp.textContent = 'A+';
  scaleBox.appendChild(scaleDown); scaleBox.appendChild(scaleRead); scaleBox.appendChild(scaleUp);
  var typeScale = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--type-scale')) || 1;
  function showScale() { scaleRead.textContent = Math.round(typeScale * 100) + '%'; }
  showScale();
  function changeScale(delta) {
    var v = Math.round((typeScale + delta) * 100) / 100;
    if (v < 0.85 || v > 1.25) { return; }
    typeScale = v;
    document.documentElement.style.setProperty('--type-scale', String(v));
    showScale();
    status.textContent = 'Saving text size\u2026';
    fetch('/__edit/typescale', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scale: v }) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) { throw new Error(j.error || r.status); } }); })
      .then(function () { status.textContent = 'Site text size ' + Math.round(v * 100) + '% saved to css/styles.css'; })
      .catch(function (err) { status.textContent = 'Text size not saved: ' + err.message; });
  }
  scaleDown.addEventListener('mousedown', function (e) { e.preventDefault(); });
  scaleUp.addEventListener('mousedown', function (e) { e.preventDefault(); });
  scaleDown.addEventListener('click', function () { changeScale(-0.05); });
  scaleUp.addEventListener('click', function () { changeScale(0.05); });
  row.appendChild(saveBtn); row.appendChild(addBtn); row.appendChild(nameBtn); row.appendChild(scaleBox); row.appendChild(exitBtn); row.appendChild(status);
  document.body.appendChild(bar);

  // ---------- per-block mini toolbar ----------
  var mini = document.createElement('div');
  mini.className = 'lsed-mini lsed-hidden';
  bar.appendChild(mini);
  function miniLabel(text) { var s = document.createElement('span'); s.className = 'lsed-label'; s.textContent = text; return s; }
  function miniButton(label, cls, title, handler) {
    var b = document.createElement('button');
    b.textContent = label;
    if (cls) { b.className = cls; }
    if (title) { b.title = title; }
    b.addEventListener('mousedown', function (e) { e.preventDefault(); }); // keep text selection
    b.addEventListener('click', handler);
    return b;
  }
  function sep() { var s = document.createElement('span'); s.className = 'lsed-sep'; return s; }
  function setPreset(el, classes, chosen) {
    classes.forEach(function (c) { if (c) { el.classList.remove(c); } });
    if (chosen) { el.classList.add(chosen); }
    if (!el.getAttribute('class')) { el.removeAttribute('class'); }
  }
  function presetSelect(title, options, el, onChange) {
    // options: [[label, className-or-empty], ...]; the empty class is the design default
    var sel = document.createElement('select');
    sel.title = title;
    var classes = options.map(function (o) { return o[1]; });
    options.forEach(function (o) {
      var opt = document.createElement('option');
      opt.textContent = title + ': ' + o[0];
      opt.value = o[1];
      if (o[1] ? el.classList.contains(o[1]) : !classes.some(function (c) { return c && el.classList.contains(c); })) { opt.selected = true; }
      sel.appendChild(opt);
    });
    sel.addEventListener('mousedown', function (e) { e.stopPropagation(); });
    sel.addEventListener('change', function () { setPreset(el, classes, sel.value); markDirty(); if (onChange) { onChange(); } });
    return sel;
  }
  function positionMini(el) { mini.classList.remove('lsed-hidden'); }
  function hideMini() { mini.classList.add('lsed-hidden'); }

  function showTextMini(el) {
    current = el; currentImg = null;
    all(main, '.lsed-active').forEach(function (i) { i.classList.remove('lsed-active'); });
    mini.innerHTML = '';
    var label = blockLabel(el);
    var b = blockOf(el);
    mini.appendChild(miniLabel({ H1: 'Title', H2: 'Heading', H3: 'Name', P: 'Paragraph', LI: 'List item', DT: 'Label', DD: 'Detail', FIGCAPTION: 'Caption', SUMMARY: 'Summary' }[el.tagName] || 'Block'));
    mini.appendChild(miniButton('B', 'lsed-fmt', 'Bold', function () { document.execCommand('bold'); markDirty(); }));
    mini.appendChild(miniButton('I', 'lsed-fmt', 'Italic', function () { document.execCommand('italic'); markDirty(); }));
    mini.appendChild(miniButton('Link', '', 'Add or edit a link on the selected text', editLink));
    mini.appendChild(sep());
    var sizeOpts = [['Small', 'text-s'], ['Normal', ''], ['Large', 'text-l']];
    if (el.tagName === 'P') { sizeOpts.push(['Lead', 'text-lead']); }
    mini.appendChild(presetSelect('Size', sizeOpts, el));
    if (el.tagName !== 'SUMMARY' && el.tagName !== 'DT') {
      mini.appendChild(presetSelect('Width', [['Narrow', 'width-narrow'], ['Normal', ''], ['Wide', 'width-wide']], el));
    }
    mini.appendChild(sep());
    mini.appendChild(miniButton('↑', '', 'Move up', function () { if (moveBlock(moveTargetOf(current), -1)) { syncNav(); markDirty(); positionMini(blockOf(current)); } }));
    mini.appendChild(miniButton('↓', '', 'Move down', function () { if (moveBlock(moveTargetOf(current), 1)) { syncNav(); markDirty(); positionMini(blockOf(current)); } }));
    mini.appendChild(sep());
    if (b.classList.contains('member') && !b.querySelector('img')) {
      mini.appendChild(miniButton('Add photo…', '', 'Add a portrait to this person', function () { addMemberPhoto(b); }));
    }
    mini.appendChild(miniButton('Duplicate ' + label, '', '', duplicateCurrent));
    var section = el.tagName === 'H2' && el.closest('section[id]');
    if (section) {
      mini.appendChild(miniButton('Delete section', 'lsed-danger', 'Remove this section and its "On this page" link', function () { deleteSection(section); }));
    } else {
      mini.appendChild(miniButton('Delete ' + label, 'lsed-danger', '', deleteCurrent));
    }
    positionMini(b);
  }
  function showImageMini(img) {
    currentImg = img; current = null;
    all(main, '.lsed-active').forEach(function (i) { i.classList.remove('lsed-active'); });
    img.classList.add('lsed-active');
    mini.innerHTML = '';
    mini.appendChild(miniLabel('Picture'));
    var sizeTarget = img.classList.contains('member-photo') ? img : (img.closest('figure') || img);
    var sizeOptions = img.classList.contains('member-photo')
      ? [['Small', 'fig-s'], ['Normal', ''], ['Large', 'fig-l']]
      : [['Small', 'fig-s'], ['Medium', 'fig-m'], ['Large', 'fig-l'], ['Full width', '']];
    mini.appendChild(presetSelect('Size', sizeOptions, sizeTarget));
    mini.appendChild(miniButton('Replace image…', '', 'Replace this picture, keeping its file name', function () { replaceImage(img); }));
    mini.appendChild(miniButton('Use another file…', '', 'Upload a new picture file and show it here', function () { swapImage(img); }));
    mini.appendChild(miniButton('Alt text…', '', 'Describe the picture for screen readers', function () {
      var v = window.prompt('Describe this picture for people who cannot see it (alt text):', img.getAttribute('alt') || '');
      if (v !== null) { img.setAttribute('alt', v.trim()); markDirty(); }
    }));
    var fig = img.closest('figure, li');
    if (fig && fig.classList.contains('member')) {
      mini.appendChild(miniButton('Remove photo', 'lsed-danger', '', function () {
        if (window.confirm('Remove this photo from the page? (The file stays in images/people/.)')) { removeBlock(img); markDirty(); hideMini(); }
      }));
    }
    positionMini(img);
  }

  function duplicateCurrent() {
    if (!current) { return; }
    var b = blockOf(current);
    var clone = b.cloneNode(true);
    all(clone, '[id]').forEach(function (n) { n.removeAttribute('id'); });
    clone.removeAttribute('id');
    insertAfterBlock(b, clone);
    var c = candidates(clone);
    c.forEach(makeEditable);
    prepImages(clone);
    markDirty();
    if (c.length) { placeCaret(c[0], false); showTextMini(c[0]); }
  }
  function deleteCurrent() {
    if (!current) { return; }
    var b = blockOf(current);
    if (!window.confirm('Delete this ' + blockLabel(current) + '? (Exit editing without saving undoes everything.)')) { return; }
    var list = candidates(main);
    var i = list.indexOf(current);
    removeBlock(b);
    markDirty();
    hideMini();
    list = candidates(main);
    var next = list[Math.min(i, list.length - 1)];
    if (next) { placeCaret(next, true); showTextMini(next); }
  }
  function deleteSection(section) {
    var id = section.id;
    if (!window.confirm('Delete the whole section "' + (section.querySelector('h2') || {}).textContent + '" and its link in "On this page"?')) { return; }
    all(main, '.page-index a[href="#' + id + '"]').forEach(function (a) { removeBlock(a.closest('li') || a); });
    removeBlock(section);
    markDirty();
    hideMini();
  }
  function editLink() {
    var sel = window.getSelection();
    if (!sel.rangeCount) { return; }
    var node = sel.anchorNode;
    var a = node && (node.nodeType === 1 ? node : node.parentNode).closest('a');
    var currentHref = a ? a.getAttribute('href') : '';
    if (!a && sel.isCollapsed) { window.alert('Select the words that should become a link first.'); return; }
    var v = window.prompt(a ? 'Edit the link address (leave empty to remove the link):' : 'Link address (https://... or a page like ../research/):', currentHref || 'https://');
    if (v === null) { return; }
    v = v.trim();
    if (a) {
      if (!v) { var parent = a.parentNode; while (a.firstChild) { parent.insertBefore(a.firstChild, a); } a.remove(); }
      else { a.setAttribute('href', v); }
    } else {
      document.execCommand('createLink', false, v);
    }
    markDirty();
  }

  // ---------- images ----------
  function companionLinks(img) {
    // Links in the same figure that point to a *different* image file (e.g. the full-size original).
    var fig = img.closest('figure');
    if (!fig) { return []; }
    var me = siteRel(img.getAttribute('src'));
    var seen = {};
    return all(fig, 'a[href]').map(function (a) { return siteRel(a.getAttribute('href')); })
      .filter(function (rel) { return rel && rel !== me && IMG_EXT.indexOf(extOf(rel)) !== -1 && !seen[rel] && (seen[rel] = true); });
  }
  function setImageFile(img, rel, size) {
    var src = PREFIX + rel + '?lsed=' + Date.now();
    img.setAttribute('src', src);
    // Pre-made small copies (images/_opt/*.webp) belong to the old file; drop them so the new file is what shows.
    img.removeAttribute('srcset'); img.removeAttribute('sizes');
    if (size) { img.setAttribute('width', size.w); img.setAttribute('height', size.h); }
  }
  function replaceImage(img) {
    var rel = siteRel(img.getAttribute('src'));
    if (!rel) { window.alert('This picture is not a file in the site folder, so it cannot be replaced here.'); return; }
    var ext = extOf(rel);
    pickFile('.' + ext + (ext === 'jpg' ? ',.jpeg' : ext === 'jpeg' ? ',.jpg' : '')).then(function (file) {
      if (!file) { return; }
      if (!sameExt(extOf(file.name), ext)) {
        window.alert('Please choose a .' + ext + ' file so the file name can stay the same, or use "Use another file…".');
        return;
      }
      status.textContent = 'Uploading…';
      return imageSize(file).then(function (size) {
        return upload(rel, file, 'replace').then(function (j) {
          if (j.status !== 200) { throw new Error(j.error || 'upload failed'); }
          setImageFile(img, rel, size);
          all(main, 'a[href]').forEach(function (a) { if (siteRel(a.getAttribute('href')) === rel) { a.setAttribute('href', PREFIX + rel); } });
          var changedAttrs = size && (String(size.w) !== img.getAttribute('data-lsed-w'));
          markDirty('Replaced ' + rel + (size ? ' — press Save to keep the new size' : ''));
          var comps = companionLinks(img);
          if (comps.length && window.confirm('This figure also links to the full-size file ' + comps[0] + ' ("Open full size"). Replace that file too?')) {
            return pickFile('.' + extOf(comps[0])).then(function (f2) {
              if (!f2) { return; }
              if (!sameExt(extOf(f2.name), extOf(comps[0]))) { window.alert('Please choose a .' + extOf(comps[0]) + ' file.'); return; }
              return upload(comps[0], f2, 'replace').then(function (j2) {
                if (j2.status !== 200) { throw new Error(j2.error || 'upload failed'); }
                status.textContent = 'Replaced both files';
              });
            });
          }
        });
      });
    }).catch(function (err) { window.alert('Image not replaced: ' + err.message); status.textContent = 'Image not replaced'; });
  }
  function swapImage(img) {
    var old = siteRel(img.getAttribute('src'));
    pickFile(IMG_EXT.map(function (e) { return '.' + e; }).join(',')).then(function (file) {
      if (!file) { return; }
      if (IMG_EXT.indexOf(extOf(file.name)) === -1) { window.alert('Please choose a PNG, JPG, GIF, WebP or SVG file.'); return; }
      var folder = (old && old.indexOf('/') !== -1) ? old.slice(0, old.lastIndexOf('/') + 1) : 'images/';
      var rel = folder + safeFileName(file.name);
      status.textContent = 'Uploading…';
      return imageSize(file).then(function (size) {
        return uploadNew(rel, file).then(function (j) {
          if (!j) { status.textContent = 'Cancelled'; return; }
          setImageFile(img, rel, size);
          if (old) {
            all(main, 'a[href]').forEach(function (a) { if (siteRel(a.getAttribute('href')) === old) { a.setAttribute('href', PREFIX + rel); } });
          }
          markDirty('Now showing ' + rel + ' — press Save to keep it');
        });
      });
    }).catch(function (err) { window.alert('Image not changed: ' + err.message); status.textContent = 'Image not changed'; });
  }
  function addMemberPhoto(card) {
    var name = (card.querySelector('.member-name') || {}).textContent || 'member';
    pickFile('.png,.jpg,.jpeg,.webp').then(function (file) {
      if (!file) { return; }
      if (['png', 'jpg', 'jpeg', 'webp'].indexOf(extOf(file.name)) === -1) { window.alert('Please choose a PNG, JPG or WebP file.'); return; }
      var rel = 'images/people/' + slugify(name) + '.' + (extOf(file.name) === 'jpeg' ? 'jpg' : extOf(file.name));
      status.textContent = 'Uploading…';
      return imageSize(file).then(function (size) {
        return uploadNew(rel, file).then(function (j) {
          if (!j) { status.textContent = 'Cancelled'; return; }
          var img = document.createElement('img');
          img.className = 'member-photo';
          img.setAttribute('alt', 'Portrait of ' + name.trim());
          setImageFile(img, rel, size);
          insertFirstChild(card, img);
          prepImages(card);
          markDirty('Photo added — press Save to keep it');
          showImageMini(img);
        });
      });
    }).catch(function (err) { window.alert('Photo not added: ' + err.message); status.textContent = 'Photo not added'; });
  }
  function addFigure(afterBlock) {
    pickFile(IMG_EXT.map(function (e) { return '.' + e; }).join(',')).then(function (file) {
      if (!file) { return; }
      if (IMG_EXT.indexOf(extOf(file.name)) === -1) { window.alert('Please choose a PNG, JPG, GIF, WebP or SVG file.'); return; }
      var alt = window.prompt('Describe this picture for people who cannot see it (alt text). For a data figure, include the legend labels and scale bars:', '');
      if (alt === null) { return; }
      var rel = 'images/' + safeFileName(file.name);
      status.textContent = 'Uploading…';
      return imageSize(file).then(function (size) {
        return uploadNew(rel, file).then(function (j) {
          if (!j) { status.textContent = 'Cancelled'; return; }
          var fig = html('<figure class="wide-figure">\n  <div class="figure-scroll">\n    <a href="' + PREFIX + rel + '">\n      <img src="' + PREFIX + rel + '" alt="">\n      <span class="visually-hidden">Open full size</span>\n    </a>\n  </div>\n  <figcaption>Caption for this figure.</figcaption>\n  <p class="figure-open"><a href="' + PREFIX + rel + '">Open full size</a></p>\n</figure>', indentBefore(afterBlock));
          var img = fig.querySelector('img');
          img.setAttribute('alt', alt.trim());
          if (size) { img.setAttribute('width', size.w); img.setAttribute('height', size.h); }
          insertAfterBlock(afterBlock, fig);
          candidates(fig).forEach(makeEditable);
          prepImages(fig);
          markDirty('Figure added \u2014 write its caption, then Save');
          var cap = fig.querySelector('figcaption');
          placeCaret(cap, false); showTextMini(cap);
        });
      });
    }).catch(function (err) { window.alert('Figure not added: ' + err.message); status.textContent = 'Figure not added'; });
  }

  // ---------- "Add..." menu ----------
  var menu = document.createElement('div');
  menu.className = 'lsed-menu lsed-hidden';
  document.body.appendChild(menu);
  function menuItem(label, handler) {
    var b = document.createElement('button');
    b.textContent = label;
    b.addEventListener('click', function () { menu.classList.add('lsed-hidden'); handler(); });
    return b;
  }
  function buildMenu() {
    menu.innerHTML = '<div class="lsed-menu-title">Add to this page</div>';
    var any = false;
    if (PAGE === 'publications') {
      menu.appendChild(menuItem('Journal paper', function () { addPublication('journal'); }));
      menu.appendChild(menuItem('Book chapter', function () { addPublication('chapter'); }));
      menu.appendChild(menuItem('Preprint (not peer reviewed)', function () { addPublication('preprint'); }));
      any = true;
    }
    if (PAGE === 'people') { menu.appendChild(menuItem('Lab member', addMember)); any = true; }
    if (PAGE === 'research' && main.querySelector('.page-index ol')) { menu.appendChild(menuItem('Research section', addSection)); any = true; }
    if (current && PAGE !== 'home') {
      menu.appendChild(menuItem('Paragraph after the selected block', function () {
        var p = document.createElement('p'); p.textContent = 'New paragraph.';
        insertAfterBlock(blockOf(current), p); makeEditable(p); markDirty(); placeCaret(p, false); showTextMini(p);
      }));
      menu.appendChild(menuItem('Figure (picture with caption) after the selected block', function () { addFigure(blockOf(current)); }));
      any = true;
    }
    if (!any) {
      var note = document.createElement('div'); note.className = 'lsed-menu-title';
      note.textContent = PAGE === 'home' ? 'The home page is edited in place; nothing to add here.' : 'Click a block first to add after it.';
      menu.appendChild(note);
    }
  }
  addBtn.addEventListener('mousedown', function (e) { e.preventDefault(); });
  addBtn.addEventListener('click', function () {
    if (menu.classList.contains('lsed-hidden')) { buildMenu(); menu.classList.remove('lsed-hidden'); }
    else { menu.classList.add('lsed-hidden'); }
  });
  document.addEventListener('mousedown', function (e) {
    if (!menu.classList.contains('lsed-hidden') && !menu.contains(e.target) && e.target !== addBtn) { menu.classList.add('lsed-hidden'); }
  });

  function addPublication(kind) {
    var headingId = { journal: 'journal-publications', chapter: 'book-chapters', preprint: 'preprints' }[kind];
    var h2 = document.getElementById(headingId);
    var list = null, n = h2 ? h2.nextElementSibling : null;
    while (n && !list) { if (n.matches('ol.cite-list')) { list = n; } else if (n.tagName === 'H2') { break; } n = n.nextElementSibling; }
    if (!list) { window.alert('Could not find the "' + kind + '" list on this page.'); return; }
    var source = kind === 'chapter'
      ? 'In: <em>Book title</em>. 2026;pages. <a href="https://doi.org/10.xxxx/xxxxx">10.xxxx/xxxxx</a>'
      : kind === 'preprint'
        ? '<em>bioRxiv</em>. 2026;2026.xx.xx.xxxxxx. <a href="https://doi.org/10.xxxx/xxxxx">10.xxxx/xxxxx</a>'
        : '<em>Journal</em>. 2026;volume(issue):pages. <a href="https://doi.org/10.xxxx/xxxxx">10.xxxx/xxxxx</a>';
    var firstEl = list.firstElementChild;
    var li = html('<li class="citation citation-' + kind + '">\n  <p class="cite-title">Title of the paper</p>\n  <p class="cite-authors">First author, <span class="author-self">Piyadasa H</span>, Last author</p>\n  <p class="cite-source">' + source + '</p>\n</li>', firstEl ? indentBefore(firstEl) : wsChild(list));
    insertFirstChild(list, li);
    candidates(li).forEach(makeEditable);
    markDirty('Fill in the new entry; the counts in the introduction update when you Save');
    var t = li.querySelector('.cite-title');
    t.scrollIntoView({ block: 'center' });
    placeCaret(t, true); showTextMini(t);
  }
  function addMember() {
    var prose = main.querySelector('.prose') || main;
    var list = prose.querySelector('ul.members');
    if (!list) {
      var h2 = all(prose, 'h2').filter(function (h) { return /lab members/i.test(h.textContent); })[0];
      var anchor = h2 ? h2 : prose.lastElementChild;
      // Put the list after the heading's following placeholder paragraph, if there is one.
      if (h2 && h2.nextElementSibling && h2.nextElementSibling.tagName === 'P') { anchor = h2.nextElementSibling; }
      list = html('<ul class="members">\n</ul>', indentBefore(anchor));
      insertAfterBlock(anchor, list);
    }
    var li = html('<li class="member">\n  <div class="member-body">\n    <h3 class="member-name">Full name</h3>\n    <p class="member-role">Role, for example PhD student</p>\n    <p class="member-bio">One or two sentences about this person\u2019s background and project.</p>\n  </div>\n</li>', wsChild(list));
    appendChildBlock(list, li);
    candidates(li).forEach(makeEditable);
    markDirty('New person added — fill in the details, add a photo if you like, then Save');
    var nm = li.querySelector('.member-name');
    nm.scrollIntoView({ block: 'center' });
    placeCaret(nm, true); showTextMini(nm);
  }
  function addSection() {
    var title = window.prompt('Heading for the new research section:', '');
    if (title === null) { return; }
    title = title.trim();
    if (!title) { return; }
    var prose = main.querySelector('.page-grid .prose');
    var nav = main.querySelector('.page-index ol');
    if (!prose || !nav) { window.alert('This page has no research sections list.'); return; }
    var id = uniqueId(slugify(title));
    var section = html('<section id="' + id + '" aria-labelledby="' + id + '-heading">\n  <h2 id="' + id + '-heading"></h2>\n  <p>Describe this direction in one or two paragraphs.</p>\n</section>', wsChild(prose));
    section.querySelector('h2').textContent = title;
    appendChildBlock(prose, section);
    var li = html('<li><a href="#' + id + '"><span class="index-label"></span></a></li>', wsChild(nav));
    li.querySelector('span').textContent = title;
    appendChildBlock(nav, li);
    candidates(section).forEach(makeEditable);
    makeEditable(li);
    syncNav();
    markDirty('Section added — you can shorten its "On this page" label too');
    section.scrollIntoView({ block: 'center' });
    placeCaret(section.querySelector('p'), false); showTextMini(section.querySelector('p'));
  }
  function syncNav() {
    // Keep "On this page" in the same order as the sections.
    var nav = main.querySelector('.page-index ol');
    if (!nav) { return; }
    var order = all(main, '.page-grid .prose section[id]').map(function (s) { return s.id; });
    var items = all(nav, 'li');
    if (!items.length) { return; }
    function idx(li) {
      var a = li.querySelector('a[href^="#"]');
      var i = a ? order.indexOf(a.getAttribute('href').slice(1)) : -1;
      return i === -1 ? 999 : i;
    }
    var sorted = items.slice().sort(function (a, b) { return idx(a) - idx(b); });
    if (sorted.every(function (li, i) { return li === items[i]; })) { return; }
    var ws = indentBefore(items[0]);
    var closing = (nav.lastChild && nav.lastChild.nodeType === 3) ? nav.lastChild.nodeValue : '\n';
    while (nav.firstChild) { nav.removeChild(nav.firstChild); }
    sorted.forEach(function (li) { nav.appendChild(document.createTextNode(ws)); nav.appendChild(li); });
    nav.appendChild(document.createTextNode(closing));
  }

  // ---------- events ----------
  main.addEventListener('focusin', function (e) {
    var el = e.target.closest && e.target.closest('.lsed');
    if (el) { showTextMini(el); }
  });
  main.addEventListener('click', function (e) {
    var img = e.target.closest && e.target.closest('img.lsed-img');
    if (img) { e.preventDefault(); e.stopPropagation(); showImageMini(img); return; }
    var a = e.target.closest && e.target.closest('a');
    if (a && (a.closest('.lsed') || a.querySelector('img'))) { e.preventDefault(); }
  }, true);
  main.addEventListener('input', function (e) {
    if (e.target.closest && e.target.closest('.lsed')) { markDirty(); }
  });
  main.addEventListener('paste', function (e) {
    var el = e.target.closest && e.target.closest('.lsed');
    if (!el) { return; }
    e.preventDefault();
    var text = (e.clipboardData || window.clipboardData).getData('text/plain');
    document.execCommand('insertText', false, text);
  });
  main.addEventListener('keydown', function (e) {
    var el = e.target.closest && e.target.closest('.lsed');
    if (!el) { return; }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); editLink(); return; }
    if (e.key === 'Escape') { el.blur(); hideMini(); return; }
    if (e.key === 'Enter' && !e.shiftKey) {
      if (el.tagName === 'SUMMARY' || el.tagName === 'DT') { e.preventDefault(); return; }
      e.preventDefault();
      var sel = window.getSelection();
      var r = sel.getRangeAt(0);
      var tail = document.createRange();
      tail.setStart(r.endContainer, r.endOffset);
      tail.setEndAfter(el.lastChild || el);
      var frag = el.lastChild ? tail.extractContents() : document.createDocumentFragment();
      var tag = /^H[1-4]$/.test(el.tagName) ? 'p' : el.tagName.toLowerCase();
      var ne = document.createElement(tag);
      if (tag === el.tagName.toLowerCase() && el.getAttribute('class')) {
        ne.setAttribute('class', el.getAttribute('class').replace(/\blsed\b/g, '').trim());
      }
      ne.appendChild(frag);
      insertAfterBlock(el, ne);
      makeEditable(ne);
      markDirty();
      placeCaret(ne, false);
      showTextMini(ne);
      return;
    }
    if (e.key === 'Backspace' && el.textContent.trim() === '' && !el.querySelector('img') && caretAtStart(el)) {
      var list = candidates(main);
      if (list.length < 2 || el.tagName === 'H1') { return; }
      e.preventDefault();
      var i = list.indexOf(el);
      removeBlock(el);
      markDirty();
      var prev = list[Math.max(0, i - 1)];
      if (prev && prev.isConnected) { placeCaret(prev, true); showTextMini(prev); } else { hideMini(); }
    }
  });

  // ---------- save ----------
  function cleanedMain() {
    var live = main.cloneNode(true);
    all(live, '.lsed').forEach(function (el) {
      el.removeAttribute('contenteditable');
      el.removeAttribute('spellcheck');
      el.classList.remove('lsed');
      if (!el.getAttribute('class')) { el.removeAttribute('class'); }
    });
    all(live, '.lsed-img').forEach(function (img) {
      img.classList.remove('lsed-img'); img.classList.remove('lsed-active');
      if (!img.getAttribute('class')) { img.removeAttribute('class'); }
      var src = img.getAttribute('src') || '';
      if (src.indexOf('?lsed=') !== -1) { img.setAttribute('src', src.split('?lsed=')[0]); }
    });
    all(live, 'details').forEach(function (d) {
      var was = d.getAttribute('data-lsed-open');
      d.removeAttribute('data-lsed-open');
      if (was === '1') { d.setAttribute('open', ''); } else { d.removeAttribute('open'); }
    });
    // Browser formatting commands produce <b>/<i>; the site uses <strong>/<em>.
    ['b:strong', 'i:em'].forEach(function (pair) {
      var from = pair.split(':')[0], to = pair.split(':')[1];
      all(live, from).forEach(function (n) {
        var r = document.createElement(to);
        while (n.firstChild) { r.appendChild(n.firstChild); }
        n.replaceWith(r);
      });
    });
    all(live, '[style]').forEach(function (n) { n.removeAttribute('style'); });
    if (PAGE === 'publications') {
      var j = live.querySelectorAll('li.citation-journal').length;
      var c = live.querySelectorAll('li.citation-chapter').length;
      var pr = live.querySelectorAll('li.citation-preprint').length;
      all(live, '.deck').forEach(function (d) {
        d.innerHTML = d.innerHTML.replace(/\d+ journal publications?, \d+ book chapters?, and \d+ preprints?/,
          j + ' journal publication' + (j === 1 ? '' : 's') + ', ' + c + ' book chapter' + (c === 1 ? '' : 's') + ', and ' + pr + ' preprint' + (pr === 1 ? '' : 's'));
      });
    }
    return live;
  }
  function doiWarnings(live) {
    var out = [];
    all(live, 'a[href^="https://doi.org/"]').forEach(function (a) {
      var h = a.getAttribute('href').replace('https://doi.org/', '').trim();
      var t = a.textContent.trim();
      if (/^10\./.test(t) && t !== h) { out.push(t + ' ≠ ' + h); }
      if (/xxxx/.test(h)) { out.push('placeholder DOI still present: ' + h); }
    });
    return out;
  }

  function save() {
    saveBtn.disabled = true;
    status.textContent = 'Saving…';
    var live = cleanedMain();
    var warn = doiWarnings(live);
    Promise.resolve()
      .then(function () {
        return fetch('/__edit/save', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: PATH, main: live.outerHTML })
        });
      })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) { throw new Error(j.error || r.status); } return j; }); })
      .then(function () {
        dirty = false;
        var t = new Date();
        status.textContent = 'Saved ' + ('0' + t.getHours()).slice(-2) + ':' + ('0' + t.getMinutes()).slice(-2) + (warn.length ? ' — check DOIs' : '');
        if (PAGE === 'publications') {
          all(main, '.deck').forEach(function (d, i) { var fresh = live.querySelectorAll('.deck')[i]; if (fresh) { d.innerHTML = fresh.innerHTML; } });
        }
        if (warn.length) { window.alert('Saved. Please check these DOI links, whose visible text and address differ or are placeholders:\n\n' + warn.join('\n')); }
      })
      .catch(function (err) {
        saveBtn.disabled = false;
        status.textContent = 'Not saved: ' + err.message;
        window.alert('Not saved: ' + err.message);
      });
  }
  saveBtn.addEventListener('click', save);
  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') { e.preventDefault(); if (dirty) { save(); } }
  });

  nameBtn.addEventListener('click', function () {
    fetch('/__edit/config', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (cfg) {
      var v = window.prompt('Lab name (header, footer and browser tab on every page):', cfg.labName || '');
      if (v === null) { return; }
      v = v.trim();
      if (!v) { return; }
      return fetch('/__edit/config', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ labName: v })
      }).then(function (r) { return r.json().then(function (j) { if (!r.ok) { throw new Error(j.error || r.status); } }); })
        .then(function () { location.reload(); });
    }).catch(function (err) { window.alert('Lab name not saved: ' + err.message); });
  });

  exitBtn.addEventListener('click', function () {
    if (dirty && !window.confirm('You have unsaved changes. Exit editing and discard them?')) { return; }
    dirty = false;
    try { localStorage.removeItem(KEY); } catch (e) {}
    location.reload();
  });
  window.addEventListener('beforeunload', function (e) {
    if (dirty) { e.preventDefault(); e.returnValue = ''; }
  });
}());
"""


def current_asset(name):
    """Serve the editor's JS/CSS from this file as it is on disk, so an updated
    preview_server.py takes effect on the next page load without a restart
    (new server endpoints still need a restart)."""
    try:
        with open(os.path.abspath(__file__), encoding="utf-8") as f:
            m = re.search(name + r' = r"""(.*?)"""', f.read(), re.S)
        if m:
            return m.group(1)
    except OSError:
        pass
    return globals()[name]


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def safe_relpath(p):
    """Return a normalised repository-relative path, or None if it escapes ROOT."""
    if not p or p.startswith(("/", "\\")) or "\\" in p:
        return None
    norm = posixpath.normpath(p)
    if norm.startswith("..") or norm == "." or "/../" in "/" + norm + "/":
        return None
    full = os.path.realpath(os.path.join(ROOT, *norm.split("/")))
    root = os.path.realpath(ROOT)
    if full != root and not full.startswith(root + os.sep):
        return None
    return norm


def backup(rel):
    ensure_backup_dir()
    src = os.path.join(ROOT, *rel.split("/"))
    if not os.path.isfile(src):
        return None
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = stamp + "_" + rel.replace("/", "__")
    dst = os.path.join(BACKUP_DIR, name)
    shutil.copy2(src, dst)
    return dst


def inject_editor(html_bytes, rel, theme=None):
    tag = ('<link rel="stylesheet" href="/__edit/editor.css">'
           '<script src="/__edit/editor.js" data-path="%s"></script>' % rel)
    text = html_bytes.decode("utf-8", errors="replace")
    text = apply_theme(text, rel, theme)
    i = text.lower().rfind("</body>")
    if i == -1:
        text = text + tag
    else:
        text = text[:i] + tag + "\n" + text[i:]
    return text.encode("utf-8")


# ---- Design previews ---------------------------------------------------
# Alternative looks live in css/themes/<name>.css (each a complete stylesheet).
# They exist only for comparing designs in the preview: the pages on disk keep
# pointing at css/styles.css.  ?theme=<name> on any page switches the look and
# remembers it in a cookie; ?theme=current goes back to the real stylesheet.
THEMES_DIR = os.path.join(ROOT, "css", "themes")
THEME_COOKIE = "labsite_theme"
_THEME_NAME_RE = re.compile(r"[a-z0-9-]{1,40}")


def available_themes():
    if not os.path.isdir(THEMES_DIR):
        return []
    names = [f[:-4] for f in os.listdir(THEMES_DIR) if f.endswith(".css")]
    return sorted(n for n in names if _THEME_NAME_RE.fullmatch(n))


def apply_theme(text, rel, theme):
    themes = available_themes()
    if not themes:
        return text
    depth = rel.count("/")
    prefix = "../" * depth
    if theme in themes:
        text = text.replace('href="%scss/styles.css"' % prefix,
                            'href="%scss/themes/%s.css"' % (prefix, theme), 1)
    links = ['<a href="?theme=current"%s>Current</a>' % (' class="on"' if theme not in themes else "")]
    for name in themes:
        label = name.replace("-", " ").capitalize()
        links.append('<a href="?theme=%s"%s>%s</a>' % (name, ' class="on"' if name == theme else "", label))
    bar = ('<div id="lsed-themes" style="position:fixed;left:.75rem;bottom:.75rem;z-index:2147483000;'
           'display:flex;flex-wrap:wrap;gap:.25rem;align-items:center;padding:.4rem .6rem;'
           'background:#1c2b33;color:#fff;border-radius:8px;font:500 13px/1.3 Inter,Helvetica,Arial,sans-serif;'
           'box-shadow:0 2px 10px rgba(0,0,0,.25)">'
           '<span style="opacity:.7;margin-right:.25rem">Design preview:</span>'
           '<style>#lsed-themes a{color:#fff;text-decoration:none;padding:.2rem .5rem;border-radius:5px;opacity:.85}'
           '#lsed-themes a:hover{background:rgba(255,255,255,.15);opacity:1}'
           '#lsed-themes a.on{background:#fff;color:#1c2b33;opacity:1;font-weight:600}</style>'
           + "".join(links) + '</div>')
    i = text.lower().rfind("</body>")
    return text[:i] + bar + "\n" + text[i:] if i != -1 else text + bar


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "LabSitePreview/1.0"

    # Pages, styles and scripts are never cached, so an edit shows on the next
    # reload.  Pictures, fonts and documents may be kept by the browser but are
    # re-checked on every visit (Last-Modified -> 304 when unchanged), so moving
    # between pages does not download megabytes of figures again.
    _REVALIDATE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif",
                       ".woff2", ".woff", ".pdf", ".ico")

    def end_headers(self):
        if getattr(self, "_pending_cookie", None):
            self.send_header("Set-Cookie", self._pending_cookie)
            self._pending_cookie = None
        path = self.path.split("?", 1)[0].lower()
        if path.endswith(self._REVALIDATE_EXT) and not path.startswith("/__edit/"):
            self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Expires", "0")
        http.server.SimpleHTTPRequestHandler.end_headers(self)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s  %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), fmt % args))

    # ---- helpers -------------------------------------------------------
    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 50 * 1024 * 1024:
            return None
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _html_rel_for_request(self):
        """Repository-relative .html path this GET resolves to, or None."""
        path = urllib.parse.urlsplit(self.path).path
        path = urllib.parse.unquote(path)
        rel = safe_relpath(path.lstrip("/")) if path.strip("/") else "."
        if rel is None:
            return None
        full = os.path.join(ROOT, *rel.split("/")) if rel != "." else ROOT
        if os.path.isdir(full):
            if not path.endswith("/"):
                return None  # SimpleHTTPRequestHandler will redirect to add the slash
            cand = posixpath.join(rel, "index.html") if rel != "." else "index.html"
            return cand if os.path.isfile(os.path.join(ROOT, *cand.split("/"))) else None
        if full.lower().endswith(EDITABLE_EXT) and os.path.isfile(full):
            return rel
        return None

    # ---- GET -----------------------------------------------------------
    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/__edit/editor.js":
            return self._send_bytes(200, current_asset("EDITOR_JS").encode("utf-8"), "text/javascript; charset=utf-8")
        if url.path == "/__edit/editor.css":
            return self._send_bytes(200, current_asset("EDITOR_CSS").encode("utf-8"), "text/css; charset=utf-8")
        if url.path == "/__edit/config":
            return self._send_json(200, {"labName": read_lab_name()})

        rel = self._html_rel_for_request()
        if rel:
            full = os.path.join(ROOT, *rel.split("/"))
            theme, set_cookie = self._theme_for_request(url)
            with open(full, "rb") as f:
                body = inject_editor(f.read(), rel, theme)
            self._pending_cookie = set_cookie
            return self._send_bytes(200, body, "text/html; charset=utf-8")
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    _pending_cookie = None

    def _theme_for_request(self, url):
        """Return (theme name or None, Set-Cookie value or None)."""
        q = urllib.parse.parse_qs(url.query)
        if "theme" in q:
            name = q["theme"][0]
            if name in available_themes():
                return name, "%s=%s; Path=/; SameSite=Lax" % (THEME_COOKIE, name)
            return None, "%s=; Path=/; Max-Age=0; SameSite=Lax" % THEME_COOKIE
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k == THEME_COOKIE and v in available_themes():
                return v, None
        return None, None

    # ---- POST ----------------------------------------------------------
    def do_POST(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/__edit/save":
            data = self._read_json()
            if not data or not isinstance(data.get("main"), str):
                return self._send_json(400, {"error": "bad request"})
            rel = safe_relpath(data.get("path", ""))
            if not rel or not rel.lower().endswith(EDITABLE_EXT):
                return self._send_json(400, {"error": "only .html files inside the site folder can be saved"})
            full = os.path.join(ROOT, *rel.split("/"))
            if not os.path.isfile(full):
                return self._send_json(404, {"error": "the editor only updates pages that already exist"})
            new_main = data["main"]
            if not new_main.lstrip().lower().startswith("<main") or not new_main.rstrip().lower().endswith("</main>"):
                return self._send_json(400, {"error": "refusing to save: content is not a complete <main> element"})
            with open(full, encoding="utf-8", newline="") as f:
                text = f.read()
            spliced = splice_main(text, new_main)
            if spliced is None:
                return self._send_json(409, {"error": "could not find exactly one <main>...</main> in " + rel})
            if spliced == text:
                return self._send_json(200, {"ok": True, "path": rel, "unchanged": True})
            bak = backup(rel)
            with open(full, "w", encoding="utf-8", newline="") as f:
                f.write(spliced)
            self.log_message("saved %s (backup %s)", rel, bak)
            return self._send_json(200, {"ok": True, "path": rel, "backup": bak})

        if url.path == "/__edit/upload":
            q = urllib.parse.parse_qs(url.query)
            rel = safe_relpath((q.get("path") or [""])[0])
            mode = (q.get("mode") or ["new"])[0]
            err = upload_target_error(rel)
            if err:
                return self._send_json(400, {"error": err})
            full = os.path.join(ROOT, *rel.split("/"))
            exists = os.path.isfile(full)
            if mode == "replace" and not exists:
                return self._send_json(404, {"error": "there is no file to replace at " + rel})
            if mode == "new" and exists:
                return self._send_json(409, {"error": "file exists", "path": rel})
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0:
                return self._send_json(400, {"error": "empty upload"})
            if n > MAX_UPLOAD:
                return self._send_json(413, {"error": "file is larger than %d MB" % (MAX_UPLOAD // (1024 * 1024))})
            body = self.rfile.read(n)
            if not looks_like(rel, body):
                return self._send_json(400, {"error": "the file content does not match its extension (." + rel.rsplit(".", 1)[-1] + ")"})
            bak = backup(rel) if exists else None
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(body)
            self.log_message("uploaded %s (%d bytes, backup %s)", rel, n, bak)
            return self._send_json(200, {"ok": True, "path": rel, "bytes": n, "backup": bak})

        if url.path == "/__edit/typescale":
            data = self._read_json()
            try:
                scale = float((data or {}).get("scale"))
            except (TypeError, ValueError):
                return self._send_json(400, {"error": "scale must be a number"})
            if not 0.85 <= scale <= 1.25:
                return self._send_json(400, {"error": "scale must be between 0.85 and 1.25"})
            if not write_type_scale(scale):
                return self._send_json(500, {"error": "could not find --type-scale in css/styles.css"})
            return self._send_json(200, {"ok": True, "scale": scale})

        if url.path == "/__edit/config":
            data = self._read_json()
            name = (data or {}).get("labName")
            if not isinstance(name, str) or not name.strip() or len(name) > 200:
                return self._send_json(400, {"error": "lab name must be 1-200 characters"})
            ok = write_lab_name(name.strip())
            if not ok:
                return self._send_json(500, {"error": "could not find labName in " + CONFIG_FILE})
            return self._send_json(200, {"ok": True, "labName": name.strip()})

        return self._send_json(404, {"error": "not found"})


MAX_UPLOAD = 40 * 1024 * 1024
UPLOAD_DIRS = ("images", "documents")
UPLOAD_EXT = {
    "png": (b"\x89PNG",), "jpg": (b"\xff\xd8\xff",), "jpeg": (b"\xff\xd8\xff",), "gif": (b"GIF8",),
    "webp": (b"RIFF",), "svg": (b"<",), "pdf": (b"%PDF",),
}
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


def upload_target_error(rel):
    """Return an error message if `rel` is not an acceptable upload path."""
    if not rel:
        return "bad path"
    parts = rel.split("/")
    if len(parts) < 2 or len(parts) > 3 or parts[0] not in UPLOAD_DIRS:
        return "pictures go in images/ (or one folder inside it); PDFs go in documents/"
    if any(not _NAME_RE.match(p) for p in parts):
        return "file and folder names may use letters, digits, dot, dash and underscore only"
    ext = parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
    if ext not in UPLOAD_EXT:
        return "allowed file types: " + ", ".join(sorted(UPLOAD_EXT))
    if parts[0] == "documents" and ext != "pdf":
        return "only PDF files go in documents/"
    if parts[0] == "images" and ext == "pdf":
        return "PDF files go in documents/"
    return None


def looks_like(rel, body):
    ext = rel.rsplit(".", 1)[-1].lower()
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n")
    if ext == "svg":
        return head.startswith(b"<")
    return any(body.startswith(sig) for sig in UPLOAD_EXT[ext])


_MAIN_OPEN_RE = re.compile(r"<main\b", re.IGNORECASE)
_MAIN_CLOSE_RE = re.compile(r"</main\s*>", re.IGNORECASE)


def splice_main(text, new_main):
    """Replace the single <main>...</main> element in `text`; None if ambiguous."""
    opens = list(_MAIN_OPEN_RE.finditer(text))
    closes = list(_MAIN_CLOSE_RE.finditer(text))
    if len(opens) != 1 or len(closes) != 1 or closes[0].start() < opens[0].end():
        return None
    return text[:opens[0].start()] + new_main + text[closes[0].end():]


_LABNAME_RE = re.compile(r'(labName\s*:\s*")((?:[^"\\]|\\.)*)(")')


def read_lab_name():
    full = os.path.join(ROOT, *CONFIG_FILE.split("/"))
    try:
        with open(full, encoding="utf-8") as f:
            m = _LABNAME_RE.search(f.read())
    except OSError:
        return None
    if not m:
        return None
    return m.group(2).replace('\\"', '"').replace("\\\\", "\\")


def write_lab_name(name):
    full = os.path.join(ROOT, *CONFIG_FILE.split("/"))
    with open(full, encoding="utf-8") as f:
        text = f.read()
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    new, n = _LABNAME_RE.subn(lambda m: m.group(1) + escaped + m.group(3), text, count=1)
    if n != 1:
        return False
    backup(CONFIG_FILE)
    with open(full, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    return True


_TYPESCALE_RE = re.compile(r"(--type-scale:\s*)([0-9.]+)(\s*;)")
STYLES_FILE = "css/styles.css"


def write_type_scale(scale):
    full = os.path.join(ROOT, *STYLES_FILE.split("/"))
    with open(full, encoding="utf-8", newline="") as f:
        text = f.read()
    value = ("%.2f" % scale).rstrip("0").rstrip(".")
    new, n = _TYPESCALE_RE.subn(lambda m: m.group(1) + value + m.group(3), text, count=1)
    if n != 1:
        return False
    if new != text:
        backup(STYLES_FILE)
        with open(full, "w", encoding="utf-8", newline="") as f:
            f.write(new)
    return True


class Server(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass  # browsers close connections early; nothing to report


def main():
    ap = argparse.ArgumentParser(description="Private preview (and editor) for the lab website.")
    ap.add_argument("--port", type=int, default=8741)
    args = ap.parse_args()
    if not os.path.isfile(os.path.join(ROOT, "index.html")):
        sys.exit("index.html not found next to the scripts folder: " + ROOT)
    handler = functools.partial(Handler, directory=ROOT)
    with Server(("127.0.0.1", args.port), handler) as httpd:
        print("Lab website - private preview")
        print("Folder : " + ROOT)
        print("Preview: http://127.0.0.1:%d/" % args.port)
        print("Editor : http://127.0.0.1:%d/#edit" % args.port)
        print("Backups: " + BACKUP_DIR)
        print("Only this computer can open these addresses. Press Control-C to stop.")
        sys.stdout.flush()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
