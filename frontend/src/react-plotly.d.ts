declare module 'react-plotly.js' {
  import { Component } from 'react';
  import { PlotParams } from 'plotly.js';

  export interface PlotProps extends Partial<PlotParams> {
    data: any[];
    layout?: any;
    config?: any;
    frames?: any[];
    useResizeHandler?: boolean;
    style?: React.CSSProperties;
    className?: string;
    divId?: string;
    onInitialized?: (figure: any, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: any, graphDiv: HTMLElement) => void;
    onPurge?: (figure: any, graphDiv: HTMLElement) => void;
    onError?: (err: any) => void;
    onClickAnnotation?: (...args: any[]) => void;
    onLegendClick?: (...args: any[]) => void;
    onLegendDoubleClick?: (...args: any[]) => void;
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
