/**
 * Card Component
 * 
 * Reusable card container for content sections
 */

import React from 'react';

export interface CardProps {
  /**
   * Card content
   */
  children: React.ReactNode;
  
  /**
   * Card title (optional)
   */
  title?: string;
  
  /**
   * Card subtitle or description (optional)
   */
  subtitle?: string;
  
  /**
   * Additional actions for the header (optional)
   */
  headerActions?: React.ReactNode;
  
  /**
   * Enable hover effect
   */
  hoverable?: boolean;
  
  /**
   * Custom padding
   */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

const PADDING_CLASSES: Record<NonNullable<CardProps['padding']>, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  headerActions,
  hoverable = false,
  padding = 'md',
  className = '',
}) => {
  const paddingClass = PADDING_CLASSES[padding];
  const hoverClass = hoverable ? 'hover:shadow-lg transition-shadow duration-200' : '';
  
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden ${hoverClass} ${className}`}>
      {(title || subtitle || headerActions) && (
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div>
              {title && <h3 className="text-lg font-bold text-gray-900">{title}</h3>}
              {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
            </div>
            {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
          </div>
        </div>
      )}
      <div className={paddingClass}>{children}</div>
    </div>
  );
};

export default Card;
