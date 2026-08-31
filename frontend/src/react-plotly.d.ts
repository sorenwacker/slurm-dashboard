declare module 'react-plotly.js' {
  import { Component } from 'react';
  import { PlotParams } from 'plotly.js';

  export interface PlotProps extends Partial<PlotParams> {
    data: Record<string, unknown>[];
    layout?: Record<string, unknown>;
    config?: Record<string, unknown>;
    frames?: Record<string, unknown>[];
    useResizeHandler?: boolean;
    style?: React.CSSProperties;
    className?: string;
    divId?: string;
    onInitialized?: (figure: unknown, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: unknown, graphDiv: HTMLElement) => void;
    onPurge?: (figure: unknown, graphDiv: HTMLElement) => void;
    onError?: (err: unknown) => void;
    onClickAnnotation?: (...args: unknown[]) => void;
    onLegendClick?: (...args: unknown[]) => void;
    onLegendDoubleClick?: (...args: unknown[]) => void;
  }

  export default class Plot extends Component<PlotProps> {}
}

declare module 'react-plotly.js/factory' {
  import { ComponentType } from 'react';
  import type { PlotProps } from 'react-plotly.js';

  export default function createPlotlyComponent(plotly: unknown): ComponentType<PlotProps>;
}

declare module 'plotly.js/lib/core' {
  const Plotly: { register: (modules: unknown[]) => void };
  export default Plotly;
}
declare module 'plotly.js/lib/bar' { const mod: unknown; export default mod; }
declare module 'plotly.js/lib/scatter' { const mod: unknown; export default mod; }
declare module 'plotly.js/lib/pie' { const mod: unknown; export default mod; }
declare module 'plotly.js/lib/indicator' { const mod: unknown; export default mod; }
