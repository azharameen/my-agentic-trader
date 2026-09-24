import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarClock, Clock3, MoreHorizontal, Pause, Play, Plus, RefreshCw, Search, Trash2, Zap } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Schedule, ScheduleInput } from '../../types/api';
import { deleteSchedule, fetchSchedules, runScheduleNow, saveSchedule, setScheduleEnabled } from '../../lib/api';

const actions: Array<{ value: ScheduleInput['action']; label: string; description: string }> = [
  { value: 'daily_scan', label: 'Daily universe scan', description: 'Scan NIFTY 100 and queue proposals for review.' },
  { value: 'groww_demat_sync', label: 'Groww holdings sync', description: 'Refresh read-only Groww Demat holdings.' },
  { value: 'monthly_universe_refresh', label: 'Monthly universe refresh', description: 'Refresh NIFTY 100 constituents and report changes.' },
];

const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

const emptyForm = (): ScheduleInput => ({
  name: '', description: '', action: 'daily_scan', trigger: 'cron', timezone: localTimezone, enabled: true,
  hour: 15, minute: 45, day_of_week: 'mon-fri',
});

const scheduleInputFrom = (schedule: Schedule): ScheduleInput => ({
  name: schedule.name,
  description: schedule.description,
  action: schedule.action,
  trigger: schedule.trigger_type,
  timezone: schedule.timezone,
  enabled: schedule.enabled,
  ...schedule.schedule,
  interval_minutes: schedule.schedule.minutes,
});

const describeSchedule = (schedule: Schedule) => schedule.trigger_type === 'interval'
  ? `Every ${schedule.schedule.minutes} minutes`
  : schedule.action === 'monthly_universe_refresh'
    ? `Monthly · day ${schedule.schedule.day} at ${String(schedule.schedule.hour).padStart(2, '0')}:${String(schedule.schedule.minute).padStart(2, '0')}`
    : `${schedule.schedule.day_of_week ?? 'Daily'} · ${String(schedule.schedule.hour).padStart(2, '0')}:${String(schedule.schedule.minute).padStart(2, '0')}`;

const formatDate = (value: string | null | undefined) => value
  ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
  : 'Not scheduled';

export const Schedules: React.FC<{ onShowToast: (message: string) => void }> = ({ onShowToast }) => {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [editorOpen, setEditorOpen] = useState(false);
  const [selected, setSelected] = useState<Schedule | null>(null);
  const [viewing, setViewing] = useState<Schedule | null>(null);
  const [form, setForm] = useState<ScheduleInput>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runRequestedAt, setRunRequestedAt] = useState<number | null>(null);

  const loadSchedules = useCallback(async () => {
    try {
      const result = await fetchSchedules();
      setSchedules(result);
      return result;
    } catch (error) {
      onShowToast(error instanceof Error ? error.message : 'Failed to load schedules');
      return [];
    } finally {
      setLoading(false);
    }
  }, [onShowToast]);

  useEffect(() => { void loadSchedules(); }, [loadSchedules]);

  const filtered = useMemo(() => schedules.filter((schedule) => {
    const matchesQuery = `${schedule.name} ${schedule.description} ${schedule.action}`.toLowerCase().includes(query.toLowerCase());
    return matchesQuery && (statusFilter === 'all' || (statusFilter === 'active' ? schedule.enabled : !schedule.enabled));
  }), [query, schedules, statusFilter]);

  const openCreate = () => { setSelected(null); setForm(emptyForm()); setEditorOpen(true); };
  const openEdit = (schedule: Schedule) => { setSelected(schedule); setForm(scheduleInputFrom(schedule)); setEditorOpen(true); setViewing(null); };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const payload: ScheduleInput = { ...form };
      if (payload.trigger === 'interval') {
        delete payload.hour;
        delete payload.minute;
        delete payload.day;
        delete payload.day_of_week;
      } else {
        delete payload.interval_minutes;
        if (payload.action === 'daily_scan') delete payload.day;
        if (payload.action !== 'daily_scan') delete payload.day_of_week;
        if (payload.action !== 'monthly_universe_refresh') delete payload.day;
      }
      await saveSchedule(payload, selected?.id);
      setEditorOpen(false);
      onShowToast(selected ? 'Schedule updated' : 'Schedule created');
      await loadSchedules();
    } catch (error) {
      onShowToast(error instanceof Error ? error.message : 'Failed to save schedule');
    } finally {
      setSaving(false);
    }
  };

  const toggleSchedule = async (schedule: Schedule) => {
    try {
      const updated = await setScheduleEnabled(schedule.id, !schedule.enabled);
      setViewing(updated);
      onShowToast(schedule.enabled ? 'Schedule paused' : 'Schedule resumed');
      await loadSchedules();
    } catch (error) {
      onShowToast(error instanceof Error ? error.message : 'Failed to update schedule');
    }
  };

  const runNow = async (schedule: Schedule) => {
    setRunningId(schedule.id);
    try {
      await runScheduleNow(schedule.id);
      onShowToast(`${schedule.name} queued to run now`);
      const startedAt = Date.now();
      setRunRequestedAt(startedAt);
      const poll = async () => {
        const latest = await loadSchedules();
        const current = latest.find((item) => item.id === schedule.id);
        const request = current?.latest_run_request;
        if (request && runRequestedAt !== null && Date.parse(request.requested_at) >= runRequestedAt - 5000 && !['PENDING', 'RUNNING'].includes(request.status)) {
          setRunningId(null);
          setRunRequestedAt(null);
        } else if (Date.now() - startedAt < 30000) {
          window.setTimeout(poll, 1500);
        } else {
          setRunningId(null);
          setRunRequestedAt(null);
        }
      };
      window.setTimeout(poll, 1500);
    } catch (error) {
      onShowToast(error instanceof Error ? error.message : 'Failed to run schedule');
      setRunningId(null);
      setRunRequestedAt(null);
    }
  };

  const removeSchedule = async (schedule: Schedule) => {
    if (!window.confirm(`Delete “${schedule.name}”?`)) return;
    try {
      await deleteSchedule(schedule.id);
      onShowToast('Schedule deleted');
      setViewing(null);
      await loadSchedules();
    } catch (error) {
      onShowToast(error instanceof Error ? error.message : 'Failed to delete schedule');
    }
  };

  const setField = <K extends keyof ScheduleInput>(key: K, value: ScheduleInput[K]) => setForm((current) => ({ ...current, [key]: value }));
  const activeCount = schedules.filter((schedule) => schedule.enabled).length;
  const nextRun = schedules.filter((schedule) => schedule.enabled && schedule.next_run).map((schedule) => schedule.next_run!).sort((left, right) => Date.parse(left) - Date.parse(right))[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary"><CalendarClock className="h-4 w-4" /> Automation</div>
          <h1 className="text-3xl font-semibold tracking-tight">Schedules</h1>
          <p className="mt-1 text-sm text-muted-foreground">Manage the background jobs that keep your trading workspace up to date.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void loadSchedules()} disabled={loading}><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh</Button>
          <Button onClick={openCreate}><Plus className="h-4 w-4" /> Add schedule</Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard label="Total schedules" value={schedules.length} note="Registered automations" icon={<CalendarClock className="h-4 w-4" />} />
        <SummaryCard label="Active" value={activeCount} note="Running on the trading engine" icon={<Play className="h-4 w-4" />} />
        <SummaryCard label="Next run" value={nextRun ? formatDate(nextRun) : '—'} note="Based on the next enabled job" icon={<Clock3 className="h-4 w-4" />} />
      </div>

      <Card>
        <CardHeader className="gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div><CardTitle className="text-lg">All automations</CardTitle><CardDescription>Changes are synchronized to the live scheduler.</CardDescription></div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search schedules" className="pl-9 sm:w-56" /></div>
            <Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="sm:w-36"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All statuses</SelectItem><SelectItem value="active">Active</SelectItem><SelectItem value="paused">Paused</SelectItem></SelectContent></Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader><TableRow><TableHead>Schedule</TableHead><TableHead>Frequency</TableHead><TableHead>Next run</TableHead><TableHead>Status</TableHead><TableHead className="w-12" /></TableRow></TableHeader>
            <TableBody>
              {filtered.map((schedule) => (
                <TableRow key={schedule.id} className="cursor-pointer" onClick={() => setViewing(schedule)}>
                  <TableCell><div className="font-medium">{schedule.name}</div><div className="mt-1 max-w-lg truncate text-xs text-muted-foreground">{schedule.description || actions.find((action) => action.value === schedule.action)?.label}</div></TableCell>
                  <TableCell><div className="font-mono text-sm">{describeSchedule(schedule)}</div><div className="mt-1 text-xs text-muted-foreground">{schedule.timezone}</div></TableCell>
                  <TableCell className="text-sm">{schedule.latest_run_request?.status === 'PENDING' || schedule.latest_run_request?.status === 'RUNNING' ? <Badge variant="outline">{schedule.latest_run_request.status}</Badge> : schedule.enabled ? formatDate(schedule.next_run) : 'Paused'}</TableCell>
                  <TableCell><Badge variant="outline" className={schedule.enabled ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-muted-foreground/30 text-muted-foreground'}>{schedule.enabled ? 'Active' : 'Paused'}</Badge></TableCell>
                  <TableCell onClick={(event) => event.stopPropagation()}><div className="flex justify-end gap-1"><Button variant="ghost" size="icon" aria-label="Run schedule now" title="Run now" disabled={runningId === schedule.id} onClick={() => void runNow(schedule)}>{runningId === schedule.id ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}</Button><Button variant="ghost" size="icon" aria-label={schedule.enabled ? 'Pause schedule' : 'Resume schedule'} onClick={() => void toggleSchedule(schedule)}>{schedule.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}</Button><Button variant="ghost" size="icon" aria-label="View schedule" onClick={() => setViewing(schedule)}><MoreHorizontal className="h-4 w-4" /></Button></div></TableCell>
                </TableRow>
              ))}
              {!loading && filtered.length === 0 && <TableRow><TableCell colSpan={5} className="h-32 text-center text-muted-foreground">No schedules match this view.</TableCell></TableRow>}
              {loading && <TableRow><TableCell colSpan={5} className="h-32 text-center text-muted-foreground">Loading schedules…</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader><DialogTitle>{selected ? 'Edit schedule' : 'Create schedule'}</DialogTitle><DialogDescription>Choose one of the supported system automations and set when it runs.</DialogDescription></DialogHeader>
          <form onSubmit={(event) => void submit(event)} className="space-y-4">
            <Field label="Name"><Input value={form.name} onChange={(event) => setField('name', event.target.value)} required maxLength={120} placeholder="Daily market scan" /></Field>
            <Field label="Automation"><Select value={form.action} onValueChange={(value) => {
              const action = value as ScheduleInput['action'];
              setForm((current) => ({ ...current, action, trigger: action === 'groww_demat_sync' ? 'interval' : 'cron', interval_minutes: action === 'groww_demat_sync' ? 15 : undefined, hour: action === 'monthly_universe_refresh' ? 6 : 15, minute: action === 'monthly_universe_refresh' ? 0 : 45, day_of_week: action === 'daily_scan' ? 'mon-fri' : undefined, day: action === 'monthly_universe_refresh' ? 1 : undefined }));
            }}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{actions.map((action) => <SelectItem key={action.value} value={action.value}>{action.label}</SelectItem>)}</SelectContent></Select></Field>
            <Field label="Description"><Input value={form.description} onChange={(event) => setField('description', event.target.value)} maxLength={500} placeholder="Optional details" /></Field>
            <Field label="Timezone"><Input value={form.timezone} onChange={(event) => setField('timezone', event.target.value)} required placeholder="Asia/Kolkata" /></Field>
            {form.action === 'groww_demat_sync' ? (
              <Field label="Run every (minutes)"><Input type="number" min={1} max={10080} value={form.interval_minutes ?? 15} onChange={(event) => setField('interval_minutes', Number(event.target.value))} required /></Field>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {form.action === 'daily_scan' && <Field label="Days"><Select value={form.day_of_week ?? 'mon-fri'} onValueChange={(value) => setField('day_of_week', value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="mon-fri">Weekdays</SelectItem><SelectItem value="mon-sun">Every day</SelectItem><SelectItem value="sat,sun">Weekends</SelectItem></SelectContent></Select></Field>}
                {form.action === 'monthly_universe_refresh' && <Field label="Day of month"><Input type="number" min={1} max={31} value={form.day ?? 1} onChange={(event) => setField('day', Number(event.target.value))} required /></Field>}
                <Field label="Hour (24h)"><Input type="number" min={0} max={23} value={form.hour ?? 0} onChange={(event) => setField('hour', Number(event.target.value))} required /></Field>
                <Field label="Minute"><Input type="number" min={0} max={59} value={form.minute ?? 0} onChange={(event) => setField('minute', Number(event.target.value))} required /></Field>
              </div>
            )}
            <div className="rounded-lg border border-border bg-muted/30 p-3 text-xs text-muted-foreground">Only the predefined daily scan, Groww sync, and monthly universe refresh actions can be scheduled.</div>
            <DialogFooter><Button type="button" variant="outline" onClick={() => setEditorOpen(false)}>Cancel</Button><Button type="submit" disabled={saving}>{saving ? 'Saving…' : selected ? 'Save changes' : 'Create schedule'}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!viewing} onOpenChange={(open) => { if (!open) setViewing(null); }}>
        <DialogContent className="sm:max-w-lg">
          {viewing && <>
            <DialogHeader><div className="flex items-center gap-2"><DialogTitle>{viewing.name}</DialogTitle><Badge variant="outline" className={viewing.enabled ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : ''}>{viewing.enabled ? 'Active' : 'Paused'}</Badge></div><DialogDescription>{viewing.description || actions.find((action) => action.value === viewing.action)?.description}</DialogDescription></DialogHeader>
            <div className="grid gap-3 rounded-lg border border-border p-4 text-sm sm:grid-cols-2"><Detail label="Automation" value={actions.find((action) => action.value === viewing.action)?.label ?? viewing.action} /><Detail label="Frequency" value={describeSchedule(viewing)} /><Detail label="Timezone" value={viewing.timezone} /><Detail label="Next run" value={viewing.enabled ? formatDate(viewing.next_run) : 'Paused'} /><Detail label="Last run" value={formatDate(viewing.latest_run_request?.completed_at ?? viewing.last_run_at)} /><Detail label="Last status" value={viewing.latest_run_request?.status ?? viewing.last_status ?? 'No run recorded'} />{runRequestedAt && runningId === viewing.id && <div className="sm:col-span-2 text-xs text-muted-foreground">Waiting for the trading engine to pick up this request…</div>}{(viewing.latest_run_request?.error || viewing.last_error) && <div className="sm:col-span-2 text-xs text-destructive">{viewing.latest_run_request?.error || viewing.last_error}</div>}</div>
            <DialogFooter className="gap-2 sm:gap-2"><Button variant="destructive" onClick={() => void removeSchedule(viewing)}><Trash2 className="h-4 w-4" /> Delete</Button><Button variant="outline" disabled={runningId === viewing.id} onClick={() => void runNow(viewing)}><Zap className="h-4 w-4" /> Run now</Button><Button variant="outline" onClick={() => void toggleSchedule(viewing)}>{viewing.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}{viewing.enabled ? 'Pause' : 'Resume'}</Button><Button onClick={() => openEdit(viewing)}>Edit schedule</Button></DialogFooter>
          </>}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const SummaryCard: React.FC<{ label: string; value: string | number; note: string; icon: React.ReactNode }> = ({ label, value, note, icon }) => (
  <Card><CardHeader className="flex-row items-start justify-between space-y-0 pb-2"><div className="space-y-1"><CardDescription>{label}</CardDescription><CardTitle className="text-2xl">{value}</CardTitle></div><div className="rounded-lg border border-border bg-muted p-2 text-primary">{icon}</div></CardHeader><CardContent><p className="text-xs text-muted-foreground">{note}</p></CardContent></Card>
);

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => <label className="grid gap-1.5 text-sm font-medium">{label}{children}</label>;
const Detail: React.FC<{ label: string; value: string }> = ({ label, value }) => <div><div className="text-xs text-muted-foreground">{label}</div><div className="mt-1 font-medium">{value}</div></div>;
