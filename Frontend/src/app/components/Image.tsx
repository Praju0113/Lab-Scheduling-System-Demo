import React from 'react';

interface ImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  fallbackSrc?: string;
  className?: string;
}

export const Image: React.FC<ImageProps> = ({ fallbackSrc = '', className, src, alt, ...rest }) => {
  const [imgSrc, setImgSrc] = React.useState(src);

  const handleError = () => {
    if (fallbackSrc) {
      setImgSrc(fallbackSrc);
    }
  };

  return (
    <img
      src={imgSrc}
      alt={alt}
      className={`object-cover ${className || ''}`}
      onError={handleError}
      {...rest}
    />
  );
};
