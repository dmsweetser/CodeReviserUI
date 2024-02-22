const unique = (iterable, key) => {
    const result = [];
    const keys = [];
 
    for (const item of iterable) {
        const keyToCheck = key ? item[key] : item;
        if (!keys.includes(keyToCheck)) {
            result.push(item);
            keys.push(keyToCheck);
        }
    }
 
    return result;
 };
 
 export default unique;