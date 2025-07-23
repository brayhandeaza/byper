import React from 'react'

type Props = {
    placeholder?: string
    onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void
    onKeyDown?: (event: React.KeyboardEvent<HTMLInputElement>) => void
}

const Input: React.FC<Props> = ({ placeholder = 'Search...', onKeyDown = (_) => {}, onChange = (_) => {} }: Props) => {

    const _onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        onChange(event)
    }

    const _onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        onKeyDown(event)
    }


    return (
        <div className='Input'>
            <input type="text" onKeyDown={_onKeyDown} onChange={_onChange} placeholder={placeholder} />
        </div>
    )
}

export default Input
