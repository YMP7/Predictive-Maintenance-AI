import React, { useEffect, useId, useRef, useState } from 'react';
import { X } from 'lucide-react';

import { Button } from './primitives';

/* Native <dialog> gives focus trapping, Esc to close and inert background for free. */

interface DialogBaseProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

function useDialog(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handle = (e: Event) => {
      e.preventDefault(); // keep React state the source of truth
      onClose();
    };
    el.addEventListener('cancel', handle);
    return () => el.removeEventListener('cancel', handle);
  }, [onClose]);
  return ref;
}

function DialogShell({ open, onClose, title, children, footer, className }: DialogBaseProps) {
  const ref = useDialog(open, onClose);
  const id = useId();
  return (
    <dialog
      ref={ref}
      className={`ax-dialog ${className ?? ''}`}
      aria-labelledby={id}
      onClick={e => {
        if (e.target === e.currentTarget) onClose(); // click on backdrop
      }}
    >
      <div className="ax-dialog__head">
        <h2 id={id}>{title}</h2>
        <Button variant="ghost" iconOnly label="Close" icon={<X aria-hidden />} onClick={onClose} />
      </div>
      <div className="ax-dialog__body">{children}</div>
      {footer && <div className="ax-dialog__foot">{footer}</div>}
    </dialog>
  );
}

export function Modal(props: DialogBaseProps) {
  return <DialogShell {...props} />;
}

/** Right-hand detail panel (part health, alarm detail, asset info). */
export function Drawer(props: DialogBaseProps) {
  return <DialogShell {...props} className="ax-drawer" />;
}

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** What will happen, in plain words, including what cannot be undone. */
  description: React.ReactNode;
  confirmLabel: string;
  danger?: boolean;
  /** Ask for a reason (shelve, reject, rollback). The reason is recorded in the audit trail. */
  requireReason?: boolean;
  busy?: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

/** Required in front of every write action. */
export function ConfirmDialog({ open, title, description, confirmLabel, danger, requireReason, busy, onConfirm, onCancel }: ConfirmDialogProps) {
  const [reason, setReason] = useState('');
  const reasonId = useId();
  const tooShort = requireReason && reason.trim().length < 5;
  const close = () => {
    setReason('');
    onCancel();
  };
  return (
    <Modal
      open={open}
      onClose={close}
      title={title}
      footer={
        <>
          <Button onClick={close}>Cancel</Button>
          <Button
            variant={danger ? 'danger' : 'primary'}
            disabled={busy || tooShort}
            onClick={() => {
              onConfirm(reason.trim());
              setReason('');
            }}
          >
            {busy ? 'Working' : confirmLabel}
          </Button>
        </>
      }
    >
      <div>{description}</div>
      {requireReason && (
        <label className="ax-field" htmlFor={reasonId}>
          <span className="ax-field__label">Reason</span>
          <textarea id={reasonId} className="ax-input" autoFocus value={reason} onChange={e => setReason(e.target.value)} required minLength={5} />
          <span className="ax-field__hint">At least 5 characters. Recorded with your name in the audit trail.</span>
        </label>
      )}
    </Modal>
  );
}
