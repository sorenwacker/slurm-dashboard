import React from 'react';

interface ChartCaptionProps {
  text: string;
  warning?: string;
}

/** One-line description under a chart of what is plotted and how it is computed. */
const ChartCaption: React.FC<ChartCaptionProps> = ({ text, warning }) => (
  <p className="chart-caption">
    {text}
    {warning && <span className="chart-caption-warning"> {warning}</span>}
  </p>
);

export default ChartCaption;
