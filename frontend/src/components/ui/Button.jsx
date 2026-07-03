import './buttons.css';

export default function Button({ variant = 'orange', size, className = '', ...props }) {
  const classes = ['btn', `btn-${variant}`, size && `btn-${size}`, className]
    .filter(Boolean)
    .join(' ');
  return <button className={classes} {...props} />;
}
