import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, LineStyle } from 'lightweight-charts';
import { Loader2, RefreshCw, Activity, Eye, EyeOff } from 'lucide-react';
import { fetchCandles, fetchUniverse, fetchSymbolLevels, ChartLevels } from '../../lib/api';
import { CandleData } from '../../types/api';
import { formatINR } from '../../lib/utils';
import { Card, CardContent, CardHeader } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface CandlestickChartProps {
  initialSymbol?: string;
}

// Compute Exponential Moving Average (EMA)
function calculateEMA(data: CandleData[], period: number): Array<{ time: string; value: number }> {
  if (data.length < period) return [];
  const k = 2 / (period + 1);
  const result: Array<{ time: string; value: number }> = [];

  // Simple Moving Average for initial seed
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += data[i].close;
  }
  let currentEMA = sum / period;
  result.push({ time: data[period - 1].time, value: currentEMA });

  for (let i = period; i < data.length; i++) {
    currentEMA = data[i].close * k + currentEMA * (1 - k);
    result.push({ time: data[i].time, value: currentEMA });
  }
  return result;
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({ initialSymbol = 'RELIANCE' }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const ema50SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ema200SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const priceLinesRef = useRef<any[]>([]);

  const [symbol, setSymbol] = useState(initialSymbol);
  const [universeSymbols, setUniverseSymbols] = useState<string[]>([]);
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [activeLevels, setActiveLevels] = useState<ChartLevels | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showEMA50, setShowEMA50] = useState(true);
  const [showEMA200, setShowEMA200] = useState(true);
  const [hoverData, setHoverData] = useState<{
    time?: string;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
  } | null>(null);

  // Load universe symbols for autocomplete
  useEffect(() => {
    fetchUniverse()
      .then((data) => setUniverseSymbols(data.symbols))
      .catch((err) => console.error('Failed to load universe', err));
  }, []);

  // Update symbol when initialSymbol prop changes
  useEffect(() => {
    if (initialSymbol) {
      setSymbol(initialSymbol);
    }
  }, [initialSymbol]);

  // Initialize Lightweight Chart instance
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#94A3B8',
      },
      grid: {
        vertLines: { color: 'rgba(51, 65, 85, 0.3)' },
        horzLines: { color: 'rgba(51, 65, 85, 0.3)' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: 'rgba(51, 65, 85, 0.6)',
      },
      timeScale: {
        borderColor: 'rgba(51, 65, 85, 0.6)',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderVisible: false,
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
    });

    const volumeSeries = chart.addHistogramSeries({
      color: '#3B82F6',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    const ema50Series = chart.addLineSeries({
      color: '#38BDF8', // Cyan/Sky blue for EMA 50
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      title: 'EMA 50',
    });

    const ema200Series = chart.addLineSeries({
      color: '#F59E0B', // Amber for EMA 200
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      title: 'EMA 200',
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    ema50SeriesRef.current = ema50Series;
    ema200SeriesRef.current = ema200Series;

    // Crosshair hover listener
    chart.subscribeCrosshairMove((param: any) => {
      if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
        setHoverData(null);
        return;
      }

      const candleData = param.seriesData?.get(candleSeries) || param.seriesPrices?.get(candleSeries);
      const volData = param.seriesData?.get(volumeSeries) || param.seriesPrices?.get(volumeSeries);

      if (candleData) {
        const timeStr =
          typeof param.time === 'string'
            ? param.time
            : typeof param.time === 'object' && param.time !== null && 'year' in param.time
            ? `${param.time.year}-${String(param.time.month).padStart(2, '0')}-${String(param.time.day).padStart(2, '0')}`
            : String(param.time);

        setHoverData({
          time: timeStr,
          open: candleData.open,
          high: candleData.high,
          low: candleData.low,
          close: candleData.close,
          volume: typeof volData === 'object' ? volData?.value : volData,
        });
      }
    });

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update chart data when candles or indicators change
  const renderChartData = (data: CandleData[]) => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current) return;

    const formattedCandles = data.map((c) => ({
      time: c.time as any,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    const formattedVolume = data.map((c) => ({
      time: c.time as any,
      value: c.volume,
      color: c.close >= c.open ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)',
    }));

    candlestickSeriesRef.current.setData(formattedCandles);
    volumeSeriesRef.current.setData(formattedVolume);

    // Calculate and set EMAs
    if (ema50SeriesRef.current) {
      if (showEMA50) {
        const ema50Data = calculateEMA(data, 50);
        ema50SeriesRef.current.setData(ema50Data as any);
        ema50SeriesRef.current.applyOptions({ visible: true });
      } else {
        ema50SeriesRef.current.applyOptions({ visible: false });
      }
    }

    if (ema200SeriesRef.current) {
      if (showEMA200) {
        const ema200Data = calculateEMA(data, 200);
        ema200SeriesRef.current.setData(ema200Data as any);
        ema200SeriesRef.current.applyOptions({ visible: true });
      } else {
        ema200SeriesRef.current.applyOptions({ visible: false });
      }
    }

    // Clear and redraw active price level overlays (ADR-032)
    if (priceLinesRef.current.length > 0 && candlestickSeriesRef.current) {
      priceLinesRef.current.forEach((line) => {
        try {
          candlestickSeriesRef.current?.removePriceLine(line);
        } catch (_) {}
      });
      priceLinesRef.current = [];
    }

    if (activeLevels && candlestickSeriesRef.current) {
      if (activeLevels.entry_price) {
        priceLinesRef.current.push(
          candlestickSeriesRef.current.createPriceLine({
            price: activeLevels.entry_price,
            color: '#3B82F6',
            lineWidth: 2,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `Entry ₹${activeLevels.entry_price.toFixed(2)}`,
          })
        );
      }
      if (activeLevels.target_price) {
        priceLinesRef.current.push(
          candlestickSeriesRef.current.createPriceLine({
            price: activeLevels.target_price,
            color: '#10B981',
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: `Target ₹${activeLevels.target_price.toFixed(2)}`,
          })
        );
      }
      if (activeLevels.trailing_stop) {
        priceLinesRef.current.push(
          candlestickSeriesRef.current.createPriceLine({
            price: activeLevels.trailing_stop,
            color: '#8B5CF6',
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: `Trailing Stop ₹${activeLevels.trailing_stop.toFixed(2)}`,
          })
        );
      } else if (activeLevels.soft_stop) {
        priceLinesRef.current.push(
          candlestickSeriesRef.current.createPriceLine({
            price: activeLevels.soft_stop,
            color: '#F59E0B',
            lineWidth: 1,
            lineStyle: LineStyle.Dotted,
            axisLabelVisible: true,
            title: `Soft Stop ₹${activeLevels.soft_stop.toFixed(2)}`,
          })
        );
      }
      if (activeLevels.hard_stop) {
        priceLinesRef.current.push(
          candlestickSeriesRef.current.createPriceLine({
            price: activeLevels.hard_stop,
            color: '#EF4444',
            lineWidth: 2,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `Hard Stop ₹${activeLevels.hard_stop.toFixed(2)}`,
          })
        );
      }
    }

    chartRef.current?.timeScale().fitContent();
  };

  // Load candle data & active levels when symbol changes
  const loadCandles = async (sym: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [data, levels] = await Promise.all([
        fetchCandles(sym),
        fetchSymbolLevels(sym).catch(() => null),
      ]);
      setCandles(data);
      setActiveLevels(levels);
    } catch (err: any) {
      console.error('Failed to load candles', err);
      setError(err.message || 'Failed to load candlestick history');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCandles(symbol);
  }, [symbol]);

  // Re-apply EMA & levels visibility when data or toggles change
  useEffect(() => {
    if (candles.length > 0) {
      renderChartData(candles);
    }
  }, [showEMA50, showEMA200, activeLevels, candles]);

  const latestCandle = candles[candles.length - 1];
  const activeInspection = hoverData || (latestCandle ? {
    time: latestCandle.time,
    open: latestCandle.open,
    high: latestCandle.high,
    low: latestCandle.low,
    close: latestCandle.close,
    volume: latestCandle.volume,
  } : null);

  return (
    <TooltipProvider>
      <Card className="shadow-2xl overflow-hidden border border-border">
        {/* Chart Toolbar */}
        <CardHeader className="p-4 sm:p-5 border-b border-border bg-card/80 flex flex-col md:flex-row md:items-center justify-between gap-4 space-y-0">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="bg-muted border border-border rounded-md px-3 py-1.5 text-foreground font-mono text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-ring transition"
              >
                {universeSymbols.length > 0 ? (
                  universeSymbols.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))
                ) : (
                  <option value={symbol}>{symbol}</option>
                )}
              </select>
            </div>

            {/* Indicator Toggles */}
            <div className="flex items-center space-x-1.5">
              <Button
                variant={showEMA50 ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => setShowEMA50(!showEMA50)}
                className={`h-7 px-2.5 text-xs font-mono gap-1 transition ${
                  showEMA50 ? 'text-sky-400 border-sky-500/30' : 'text-muted-foreground'
                }`}
              >
                <Activity className="w-3 h-3 text-sky-400" />
                <span>EMA 50</span>
                {showEMA50 ? <Eye className="w-3 h-3 ml-0.5" /> : <EyeOff className="w-3 h-3 ml-0.5 opacity-50" />}
              </Button>

              <Button
                variant={showEMA200 ? 'secondary' : 'outline'}
                size="sm"
                onClick={() => setShowEMA200(!showEMA200)}
                className={`h-7 px-2.5 text-xs font-mono gap-1 transition ${
                  showEMA200 ? 'text-amber-400 border-amber-500/30' : 'text-muted-foreground'
                }`}
              >
                <Activity className="w-3 h-3 text-amber-400" />
                <span>EMA 200</span>
                {showEMA200 ? <Eye className="w-3 h-3 ml-0.5" /> : <EyeOff className="w-3 h-3 ml-0.5 opacity-50" />}
              </Button>
            </div>

            {/* Live OHLCV Inspector Ribbon */}
            {activeInspection && (
              <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono bg-muted/40 px-3 py-1.5 rounded-md border border-border/60">
                <span className="text-muted-foreground">O: <strong className="text-foreground">₹{formatINR(activeInspection.open)}</strong></span>
                <span className="text-muted-foreground">H: <strong className="text-emerald-400">₹{formatINR(activeInspection.high)}</strong></span>
                <span className="text-muted-foreground">L: <strong className="text-rose-400">₹{formatINR(activeInspection.low)}</strong></span>
                <span className="text-muted-foreground">C: <strong className="text-foreground font-bold">₹{formatINR(activeInspection.close)}</strong></span>
                {activeInspection.volume !== undefined && (
                  <span className="text-muted-foreground">Vol: <strong className="text-primary">{activeInspection.volume.toLocaleString()}</strong></span>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => loadCandles(symbol)}
                  disabled={isLoading}
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                >
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin text-primary" /> : <RefreshCw className="w-4 h-4" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Reload daily candlestick & volume data for {symbol}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </CardHeader>

        {/* Chart Canvas */}
        <CardContent className="p-0 relative h-[560px] w-full bg-background/50">
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 text-rose-400 text-xs p-4 text-center z-10">
              {error}
            </div>
          )}
          <div ref={chartContainerRef} className="w-full h-full" />
        </CardContent>
      </Card>
    </TooltipProvider>
  );
};
